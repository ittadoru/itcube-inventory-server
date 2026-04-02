import csv
import json
import os
import secrets
from pathlib import Path

import requests

API_BASE = os.getenv("API_BASE_URL", "https://it-cube.ittado.online/api").rstrip("/")
API_KEY = os.environ.get("API_KEY")
DEVICE_KEY = os.getenv("DEVICE_KEY", secrets.token_urlsafe(32))
CSV_PATH = Path(os.getenv("ITEMS_CSV", "items.csv"))
TIMEOUT = 20


def fail(message: str) -> None:
    raise SystemExit(message)


def parse_properties(raw: str | None) -> dict:
    value = (raw or "").strip()
    if not value:
        return {}

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        fail(f"Invalid properties_json: {value!r}. Error: {exc}")

    if not isinstance(parsed, dict):
        fail(f"properties_json must be a JSON object, got: {type(parsed).__name__}")

    return parsed


def auth_token() -> str:
    if not API_KEY:
        fail("Set API_KEY env with current key from /admin")

    response = requests.post(
        f"{API_BASE}/auth/login-by-api-key",
        json={"api_key": API_KEY, "device_key": DEVICE_KEY},
        timeout=TIMEOUT,
    )

    if response.status_code >= 400:
        fail(f"Auth failed: {response.status_code} {response.text}")

    payload = response.json()
    token = payload.get("access_token")
    if not token:
        fail("Auth response does not contain access_token")

    print(f"Authenticated as user_id={payload.get('user_id')} username={payload.get('username')}")
    return token


def main() -> None:
    if not CSV_PATH.exists():
        fail(f"CSV file not found: {CSV_PATH}")

    token = auth_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    required_columns = {"inventory_number", "item_type", "item_name", "properties_json"}

    created = 0
    failed = 0

    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            fail("CSV has no header")

        missing = required_columns - set(reader.fieldnames)
        if missing:
            fail(f"CSV missing columns: {', '.join(sorted(missing))}")

        for line_no, row in enumerate(reader, start=2):
            inventory_number = (row.get("inventory_number") or "").strip()
            item_type = (row.get("item_type") or "").strip()
            item_name = (row.get("item_name") or "").strip()

            if not inventory_number or not item_type or not item_name:
                failed += 1
                print(f"ERR line {line_no}: required fields are empty")
                continue

            try:
                payload = {
                    "inventory_number": inventory_number,
                    "item_type": item_type,
                    "item_name": item_name,
                    "properties_json": parse_properties(row.get("properties_json")),
                }
            except SystemExit as exc:
                failed += 1
                print(f"ERR line {line_no}: {exc}")
                continue

            r = requests.post(f"{API_BASE}/items", json=payload, headers=headers, timeout=TIMEOUT)

            if r.status_code in (200, 201):
                created += 1
                print(f"OK  line {line_no}: {inventory_number}")
            else:
                failed += 1
                print(f"ERR line {line_no}: {inventory_number} -> {r.status_code} {r.text}")

    print(f"Done. created={created}, failed={failed}")


if __name__ == "__main__":
    main()
