"""
Input parsing + deterministic validation.

Layer 1 of the three-layer quality pipeline:
  code catches HARD issues (missing required fields, TBD, unknown enum values)
  -> flags are injected into the model context (layer 2: model interprets soft
  conflicts per decision rules) -> humans arbitrate in the UI (layer 3).
"""
from __future__ import annotations
import io
import json
import re
import zipfile
from .schema import (
    ANALYSIS_REQUIRED_TABLES,
    COLUMN_ALIASES,
    COLUMN_ALIAS_PATTERNS,
    ENUM_COLUMNS,
    LEVEL_COLUMNS,
    LEVEL_VALUES,
    MISSING_VALUES,
    SCHEMA_VERSION,
    SCORING,
    TABLE_SPECS,
)


class WorkbookFormatError(ValueError):
    """Raised when uploaded bytes are not a readable OOXML Excel workbook."""


def validate_xlsx_upload(data: bytes) -> None:
    """Validate workbook content without trusting its name or browser MIME type."""
    if not data:
        raise WorkbookFormatError("The uploaded file is empty.")

    # Legacy .xls and password-encrypted OOXML both use the OLE compound format.
    if data.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):
        raise WorkbookFormatError(
            "This is a legacy .xls or encrypted Office file. "
            "Save an unencrypted copy as .xlsx and upload it again."
        )

    stream = io.BytesIO(data)
    if not zipfile.is_zipfile(stream):
        raise WorkbookFormatError(
            "The file content is not an Excel .xlsx workbook. "
            "Open it in Excel or LibreOffice and save it as .xlsx."
        )

    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            names = set(archive.namelist())
            required = {"[Content_Types].xml", "xl/workbook.xml"}
            if not required.issubset(names):
                raise WorkbookFormatError(
                    "The upload is a ZIP file, but it does not contain an Excel workbook."
                )
            if any(info.flag_bits & 0x1 for info in archive.infolist()):
                raise WorkbookFormatError(
                    "Password-protected workbooks are not supported. "
                    "Upload an unencrypted .xlsx copy."
                )
            total_uncompressed = sum(info.file_size for info in archive.infolist())
            if total_uncompressed > 200 * 1024 * 1024:
                raise WorkbookFormatError(
                    "The expanded workbook is too large to process safely."
                )
            damaged_entry = archive.testzip()
            if damaged_entry:
                raise WorkbookFormatError(
                    f"The workbook archive is damaged near '{damaged_entry}'."
                )
    except WorkbookFormatError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise WorkbookFormatError(
            "The workbook could not be read. Save a fresh .xlsx copy and try again."
        ) from exc


def _clean(v):
    if v is None:
        return ""
    return str(v).strip()


def _is_missing(v) -> bool:
    return _clean(v).lower() in MISSING_VALUES


def _norm(v) -> str:
    return " ".join(_clean(v).lower().split())


def _trim_trailing_empty(row) -> list:
    values = list(row)
    while values and not _clean(values[-1]):
        values.pop()
    return values


def _add_schema_issue(report: dict, severity: str, code: str, table: str,
                      location: str, expected: str, actual: str, action: str,
                      detail: str) -> None:
    report["issues"].append({
        "severity": severity,
        "code": code,
        "table": table,
        "location": location,
        "expected": expected,
        "actual": actual,
        "action": action,
        "detail": detail,
    })
    if severity == "BLOCKER":
        report["blocking"] = True


def _header_status(table: str, expected: str, actual: str) -> str:
    """Return exact, alias, or mismatch for one header at a fixed position."""
    if _norm(actual) == _norm(expected):
        return "exact"
    aliases = COLUMN_ALIASES.get(table, {}).get(expected, set())
    if any(_norm(actual) == _norm(alias) for alias in aliases):
        return "alias"
    for pattern in COLUMN_ALIAS_PATTERNS.get(table, {}).get(expected, []):
        if re.fullmatch(pattern, _norm(actual), flags=re.IGNORECASE):
            return "alias"
    return "mismatch"


def _find_sheet(wb, key: str, position: int, claimed: set[str], report: dict):
    """Resolve by canonical letter/name; use position only when unambiguous."""
    letter, suffix = key.split("_", 1)
    names = [n for n in wb.sheetnames if n not in claimed]
    exact = [n for n in names if _norm(n) == _norm(key)]
    prefixed = [n for n in names if _norm(n).startswith(letter.lower() + "_")]
    suffix_match = [n for n in names if _norm(n) == _norm(suffix)]
    candidates = exact or prefixed or suffix_match

    if len(candidates) > 1:
        _add_schema_issue(
            report, "BLOCKER", "DUPLICATE_SHEET", key, "sheet",
            "one matching sheet", ", ".join(candidates), "rename or remove duplicates",
            f"Multiple sheets could map to {key}; positional mapping would be ambiguous.",
        )
    if candidates:
        name = candidates[0]
    else:
        name = None
        # A fully custom sheet title is accepted only when its fixed position is
        # not visibly occupied by another A-H sheet. This prevents a missing F
        # sheet from shifting G into the F schema.
        if position < len(wb.sheetnames):
            positional = wb.sheetnames[position]
            visible_prefix = re.match(r"^([a-h])(?:_|\b)", _norm(positional))
            if positional not in claimed and not visible_prefix:
                name = positional
                _add_schema_issue(
                    report, "WARNING", "POSITIONAL_SHEET_MAPPING", key, "sheet",
                    key, positional, f"mapped position {position + 1} to {key}",
                    "Sheet title is non-standard; fixed workbook order was used.",
                )
    if name is None:
        severity = "BLOCKER" if key in ANALYSIS_REQUIRED_TABLES else "WARNING"
        action = "add the required sheet" if severity == "BLOCKER" else "continue with a data gap"
        _add_schema_issue(
            report, severity, "MISSING_SHEET", key, "sheet", key, "missing", action,
            f"Sheet {key} was not found.",
        )
        return None

    claimed.add(name)
    report["sheet_map"][key] = name
    if _norm(name) != _norm(key) and not any(
            i["code"] == "POSITIONAL_SHEET_MAPPING" and i["table"] == key
            for i in report["issues"]):
        _add_schema_issue(
            report, "INFO", "SHEET_ALIAS", key, "sheet", key, name,
            f"mapped to {key}", "Sheet name was recognized by its canonical A-H prefix.",
        )
    return wb[name]


def load_workbook_with_report(file) -> tuple[dict, dict]:
    """Parse an xlsx and return canonical tables plus a schema validation report.

    Data rows are mapped by fixed column position only after column count and
    header/approved-alias checks. The raw Excel headers never leak into business
    rules, scoring, or prompt assembly.
    """
    from openpyxl import load_workbook as _lw
    wb = _lw(file, data_only=True, read_only=True)
    tables = {}
    report = {
        "schema_version": SCHEMA_VERSION,
        "blocking": False,
        "issues": [],
        "sheet_map": {},
    }
    claimed = set()
    for position, (key, spec) in enumerate(TABLE_SPECS.items()):
        sheet = _find_sheet(wb, key, position, claimed, report)
        if sheet is None:
            tables[key] = None
            continue
        rows = list(sheet.iter_rows(values_only=True))
        rows = [r for r in rows if any(_clean(c) for c in r)]
        if not rows:
            tables[key] = None
            severity = "BLOCKER" if key in ANALYSIS_REQUIRED_TABLES else "WARNING"
            _add_schema_issue(
                report, severity, "EMPTY_SHEET", key, "sheet", "data rows", "empty",
                "add data before analysis", f"Sheet {sheet.title} is empty.",
            )
            continue
        if spec.get("key_value"):
            used_columns = max(len(_trim_trailing_empty(r)) for r in rows)
            if used_columns != 2:
                _add_schema_issue(
                    report, "BLOCKER", "COLUMN_COUNT", key, "sheet",
                    "2 key/value columns", str(used_columns), "fix the sheet structure",
                    f"{key} must contain exactly two used columns.",
                )
            first = [_norm(v) for v in _trim_trailing_empty(rows[0])[:2]]
            has_header = len(first) == 2 and first[0] == "field" and first[1] in {"information", "value"}
            data_rows = rows[1:] if has_header else rows
            if has_header:
                _add_schema_issue(
                    report, "INFO", "KEY_VALUE_HEADER", key, "row 1",
                    "Field | Information", " | ".join(_clean(v) for v in rows[0][:2]),
                    "header excluded from campaign data", "Key/value header recognized.",
                )
            table, seen = {}, set()
            for r in data_rows:
                field = _clean(r[0]) if r else ""
                if not field:
                    continue
                norm_field = _norm(field)
                if norm_field in seen:
                    _add_schema_issue(
                        report, "BLOCKER", "DUPLICATE_FIELD", key, field,
                        "unique campaign fields", field, "remove or merge the duplicate",
                        f"Campaign field '{field}' appears more than once.",
                    )
                seen.add(norm_field)
                table[field] = _clean(r[1]) if len(r) > 1 else ""
            tables[key] = table
        else:
            header = [_clean(c) for c in _trim_trailing_empty(rows[0])]
            expected = spec["columns"]
            if len(header) != len(expected):
                _add_schema_issue(
                    report, "BLOCKER", "COLUMN_COUNT", key, "row 1",
                    str(len(expected)), str(len(header)), "restore the template column count",
                    f"{key} has {len(header)} used columns; schema {SCHEMA_VERSION} expects {len(expected)}.",
                )
            for index, expected_name in enumerate(expected):
                actual_name = header[index] if index < len(header) else "missing"
                status = _header_status(key, expected_name, actual_name)
                if status == "alias":
                    _add_schema_issue(
                        report, "WARNING", "HEADER_ALIAS", key, f"column {index + 1}",
                        expected_name, actual_name, f"mapped to {expected_name}",
                        "Approved header alias accepted; downstream data uses the canonical field.",
                    )
                elif status == "mismatch":
                    _add_schema_issue(
                        report, "BLOCKER", "HEADER_MISMATCH", key, f"column {index + 1}",
                        expected_name, actual_name, "rename the column or add an approved alias",
                        "Column position is fixed, but its header does not match the schema.",
                    )
            tables[key] = [
                {expected[i]: _clean(r[i]) if i < len(r) else "" for i in range(len(expected))}
                for r in rows[1:] if any(_clean(c) for c in r)
            ]
    wb.close()
    return tables, report


def load_workbook(file) -> dict:
    """Backward-compatible canonical workbook loader."""
    tables, _ = load_workbook_with_report(file)
    return tables


def load_json(file) -> dict:
    data = json.load(file) if hasattr(file, "read") else json.loads(file)
    return {k: data.get(k) for k in TABLE_SPECS}


def validate(tables: dict) -> list[dict]:
    """Deterministic pre-check. Returns a list of flag dicts:
    {type: MISSING_TABLE|MISSING_FIELD|UNKNOWN_VALUE, table, row, field, raw, detail}
    """
    flags = []
    for key, spec in TABLE_SPECS.items():
        t = tables.get(key)
        if t is None:
            flags.append({"type": "MISSING_TABLE", "table": key, "row": "", "field": "",
                          "raw": "", "detail": f"Sheet '{key}' not found or empty"})
            continue
        if spec.get("key_value"):
            for f in spec.get("required", []):
                if f not in t or _is_missing(t.get(f)):
                    flags.append({"type": "MISSING_FIELD", "table": key, "row": f,
                                  "field": f, "raw": _clean(t.get(f, "")),
                                  "detail": f"Required campaign field '{f}' is missing"})
            continue
        label_col = spec["columns"][0]
        seen_labels = set()
        for row in t:
            label = row.get(label_col, "?")
            normalized_label = _norm(label)
            if normalized_label and normalized_label in seen_labels:
                flags.append({"type": "DUPLICATE_KEY", "table": key, "row": label,
                              "field": label_col, "raw": label,
                              "detail": f"'{label}': duplicate key in '{label_col}' - key-based joins "
                                        "would otherwise overwrite one row; owner must merge or choose the source row"})
            seen_labels.add(normalized_label)
            for f in spec.get("required", []):
                if _is_missing(row.get(f)):
                    flags.append({"type": "MISSING_FIELD", "table": key, "row": label,
                                  "field": f, "raw": row.get(f, ""),
                                  "detail": f"'{label}': required field '{f}' is '{row.get(f) or 'empty'}'"})
            for f, v in row.items():
                if _clean(v).lower() == "tbd" and f not in spec.get("required", []):
                    flags.append({"type": "MISSING_FIELD", "table": key, "row": label,
                                  "field": f, "raw": v,
                                  "detail": f"'{label}': field '{f}' is explicitly TBD"})
                if f in LEVEL_COLUMNS and not _is_missing(v) \
                        and _clean(v).lower() not in LEVEL_VALUES \
                        and not _clean(v).upper().startswith("P"):
                    flags.append({"type": "UNKNOWN_VALUE", "table": key, "row": label,
                                  "field": f, "raw": v,
                                  "detail": f"'{label}': value '{v}' in '{f}' is not in the known vocabulary"})
                if f in ENUM_COLUMNS and not _is_missing(v) \
                        and _clean(v).upper() not in ENUM_COLUMNS[f]:
                    allowed = ", ".join(sorted(ENUM_COLUMNS[f]))
                    flags.append({"type": "UNKNOWN_VALUE", "table": key, "row": label,
                                  "field": f, "raw": v,
                                  "detail": f"'{label}': value '{v}' in '{f}' is invalid; expected one of {allowed}"})
    flags.extend(validate_scoring_inputs(tables, flags))
    flags.extend(validate_coverage(tables))
    return flags


def validate_scoring_inputs(tables: dict, existing_flags: list[dict] | None = None) -> list[dict]:
    """Surface inputs that make a score incomplete instead of coercing them to zero."""
    existing_flags = existing_flags or []
    existing = {(f.get("table"), _norm(f.get("row")), f.get("field")) for f in existing_flags}
    flags = []
    products_by_market = {}
    for row in (tables.get("C_Products") or []):
        products_by_market.setdefault(_norm(row.get("Market")), []).append(row)

    for market_row in (tables.get("B_Markets") or []):
        market = _clean(market_row.get("Market"))
        market_key = _norm(market)
        if _is_missing(market_row.get("Search Growth vs Baseline")) \
                and ("B_Markets", market_key, "Search Growth vs Baseline") not in existing:
            flags.append({
                "type": "SCORING_INPUT_MISSING", "table": "B_Markets", "row": market,
                "field": "Search Growth vs Baseline", "raw": market_row.get("Search Growth vs Baseline", ""),
                "detail": f"'{market}': scoring input 'Search Growth vs Baseline' is missing; "
                          "score and tier will be withheld rather than treating it as 0",
            })
        product_rows = products_by_market.get(market_key, [])
        if len(product_rows) != 1:
            if not product_rows:
                flags.append({
                    "type": "SCORING_INPUT_MISSING", "table": "C_Products", "row": market,
                    "field": "Market", "raw": "",
                    "detail": f"'{market}': no unique product row is available; score and tier will be withheld",
                })
            continue
        product_row = product_rows[0]
        for field in SCORING["product_weights"]:
            if _is_missing(product_row.get(field)):
                flags.append({
                    "type": "SCORING_INPUT_MISSING", "table": "C_Products", "row": market,
                    "field": field, "raw": product_row.get(field, ""),
                    "detail": f"'{market}': scoring input '{field}' is missing; score and tier "
                              "will be withheld rather than renormalizing incomplete product data",
                })
    return flags


def validate_coverage(tables: dict) -> list[dict]:
    """Cross-check coverage tokens (E/G tables) against known markets+aliases.
    An unrecognized token would silently exclude a channel/asset - surface it."""
    from .schema import alias_map
    aliases_all = alias_map()
    markets = [(_clean(r.get("Market")).lower()) for r in (tables.get("B_Markets") or [])]
    known = set(markets) | {"all markets", "all", "selected markets", "selected"}
    for m in markets:
        known |= aliases_all.get(m, set())
        for full, ali in aliases_all.items():
            if m in ali or m == full:
                known.add(full); known |= ali
    flags = []
    for key, col, label_col in (("E_Channels", "Market Coverage", "Channel"),
                                 ("G_Assets", "Required Markets", "Asset Type")):
        for row in (tables.get(key) or []):
            cell = _clean(row.get(col, ""))
            if _is_missing(cell):
                continue
            if "selected" in cell.lower():
                flags.append({"type": "AMBIGUOUS_COVERAGE", "table": key,
                              "row": row.get(label_col, "?"), "field": col, "raw": cell,
                              "detail": f"'{row.get(label_col)}': coverage is '{cell}' - does not confirm "
                                        f"eligibility for any specific market; owner must confirm before use"})
                continue
            for tok in split_list(cell):
                if tok.lower() not in known:
                    flags.append({"type": "UNMAPPED_MARKET", "table": key,
                                  "row": row.get(label_col, "?"), "field": col, "raw": tok,
                                  "detail": f"'{row.get(label_col)}': coverage token '{tok}' does not match "
                                            f"any target market or known alias - it would be silently "
                                            f"excluded from matching. Confirm the mapping in Step 2 "
                                            f"or fix the data."})
    return flags


def parse_markets(tables: dict) -> list[str]:
    b = tables.get("B_Markets") or []
    return [r.get("Market") for r in b if _clean(r.get("Market"))]


def split_list(cell: str) -> list[str]:
    out = []
    for part in _clean(cell).replace(";", ",").split(","):
        p = part.strip()
        if p and p.lower() not in MISSING_VALUES:
            out.append(p)
    return out
