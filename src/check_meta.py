"""Read-only Meta credential check. Does not create or publish posts."""
import os, requests

VERSION = os.getenv("META_GRAPH_VERSION", "v27.0")
BASE = "https://graph.facebook.com/" + VERSION + "/"

def check(label, identifier, token, fields, expected_name):
    if not identifier or not token:
        print(label + ": missing ID or secret in GitHub Actions settings")
        return False
    try:
        r = requests.get(BASE + identifier, params={"fields": fields},
                         headers={"Authorization": "Bearer " + token}, timeout=30)
        payload = r.json()
    except (requests.RequestException, ValueError):
        print(label + ": network or response error")
        return False
    if not r.ok or "error" in payload:
        e = payload.get("error") or {}
        print(label + ": API rejected credential (code " + str(e.get("code", r.status_code)) + ")")
        return False
    if str(payload.get("id")) != identifier:
        print(label + ": account ID does not match")
        return False
    if expected_name and payload.get("username", "").lower() != expected_name:
        print(label + ": username does not match expected account")
        return False
    print(label + ": access verified for account ID " + identifier)
    return True

def main():
    page_ok = check("Facebook Page", os.getenv("META_PAGE_ID","").strip(),
                    os.getenv("META_PAGE_TOKEN","").strip(), "id,name", None)
    ig_ok = check("Instagram", os.getenv("META_IG_USER_ID","").strip(),
                  os.getenv("META_IG_TOKEN","").strip(), "id,username", "unlearnthefear")
    if not (page_ok and ig_ok):
        raise SystemExit("Read-only credential test failed. No posts were published.")
    print("Both credentials verified. No posts were published.")

if __name__ == "__main__":
    main()
