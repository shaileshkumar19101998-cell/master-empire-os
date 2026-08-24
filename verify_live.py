import urllib.request
import urllib.error

base_url = "https://master-empire-os.onrender.com"

def check_url(name, path, expected_code):
    url = base_url + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req)
        status = resp.getcode()
        print(f"{name:35} : HTTP {status} {'[PASS]' if status == expected_code else '[FAIL]'}")
    except urllib.error.HTTPError as e:
        print(f"{name:35} : HTTP {e.code} {'[PASS]' if e.code == expected_code else '[FAIL]'}")
    except Exception as err:
        print(f"{name:35} : ERROR ({str(err)}) [FAIL]")

print("\n" + "="*60)
print("  LIVE PRODUCTION VERIFICATION (RENDER PROD)")
print("="*60 + "\n")

check_url("1. Storefront (GET /)", "/", 200)
check_url("2. Robots (GET /robots.txt)", "/robots.txt", 200)
check_url("3. Sitemap (GET /sitemap.xml)", "/sitemap.xml", 200)
check_url("4. API Docs (GET /docs)", "/docs", 200)
check_url("5. Command Center (Unauthorized)", "/admin/bi-dashboard", 401)

print("\n" + "="*60 + "\n")