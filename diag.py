"""Network diagnostic: python diag.py"""
import json, socket, urllib.request

print("1) System/env proxies detected by Python:")
print("  ", urllib.request.getproxies() or "(none)")

host = "dashscope.aliyuncs.com"
print(f"\n2) DNS for {host}:")
try:
    ip = socket.gethostbyname(host); print("  ", ip)
except Exception as e:
    print("   DNS FAILED:", e)

print("\n3) Direct TCP connect to 443 (no proxy):")
try:
    s = socket.create_connection((host, 443), timeout=10); s.close()
    print("   OK - direct connection works")
except Exception as e:
    print("   FAILED:", e)

print("\n4) HTTPS request bypassing all proxies:")
try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        headers={"Authorization": "Bearer test"})
    opener.open(req, timeout=15)
except urllib.error.HTTPError as e:
    print(f"   Reached server (HTTP {e.code}) - network is FINE, "
          "401/403 here just means the test key is fake")
except Exception as e:
    print("   FAILED:", e)

print("\n5) HTTPS request with default proxy behavior:")
try:
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        headers={"Authorization": "Bearer test"})
    urllib.request.urlopen(req, timeout=15)
except urllib.error.HTTPError as e:
    print(f"   Reached server (HTTP {e.code})")
except Exception as e:
    print("   FAILED:", e)
