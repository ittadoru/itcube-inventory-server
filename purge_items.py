import os
import secrets

import requests

API_BASE = os.getenv("API_BASE_URL", "https://it-cube.ittado.online/api").rstrip("/")
API_KEY = os.environ.get("API_KEY")
DEVICE_KEY = os.getenv("DEVICE_KEY", secrets.token_urlsafe(32))
TIMEOUT = 20


def fail(message: str) -> None:
    raise SystemExit(message)


def auth_headers() -> dict[str, str]:
    if not API_KEY:
        fail("Set API_KEY env with current key from /admin")

    auth = requests.post(
        f"{API_BASE}/auth/login-by-api-key",
        json={"api_key": API_KEY, "device_key": DEVICE_KEY},
        timeout=TIMEOUT,
    )
    if auth.status_code >= 400:
        fail(f"Auth failed: {auth.status_code} {auth.text}")

    token = auth.json().get("access_token")
    if not token:
        fail("Auth response does not contain access_token")

    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def main() -> None:
    headers = auth_headers()
    response = requests.get(f"{API_BASE}/items", headers=headers, timeout=TIMEOUT)
    if response.status_code >= 400:
        fail(f"Load items failed: {response.status_code} {response.text}")

    items = response.json()
    if not items:
        print("No items to delete")
        return

    confirm = os.getenv("CONFIRM_DELETE_ALL_ITEMS", "false").lower() == "true"
    if not confirm:
        fail("Set CONFIRM_DELETE_ALL_ITEMS=true to proceed")

    deleted = 0
    failed = 0
    for item in items:
        item_id = item["id"]
        r = requests.delete(f"{API_BASE}/items/{item_id}", headers=headers, timeout=TIMEOUT)
        if r.status_code == 204:
            deleted += 1
            print(f"OK  deleted item_id={item_id} inv={item.get('inventory_number')}")
        else:
            failed += 1
            print(f"ERR delete item_id={item_id}: {r.status_code} {r.text}")

    print(f"Done. deleted={deleted}, failed={failed}")


if __name__ == "__main__":
    main()
