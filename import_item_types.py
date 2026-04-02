import csv
import os
import secrets
from pathlib import Path

import requests

API_BASE = os.getenv("API_BASE_URL", "https://it-cube.ittado.online/api").rstrip("/")
API_KEY = os.environ.get("API_KEY")
DEVICE_KEY = os.getenv("DEVICE_KEY", secrets.token_urlsafe(32))
CSV_PATH = Path(os.getenv("ITEM_TYPES_CSV", "item_types.csv"))
TIMEOUT = 20


def fail(message: str) -> None:
    raise SystemExit(message)


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


def read_type_names(csv_path: Path) -> list[str]:
    if not csv_path.exists():
        fail(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            fail("CSV has no header")

        candidates = ["item_type", "name", "type"]
        source_column = next((c for c in candidates if c in reader.fieldnames), None)
        if source_column is None:
            fail("CSV must contain one of columns: item_type, name, type")

        result: list[str] = []
        seen = set()
        for row in reader:
            value = (row.get(source_column) or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)

        return result


def main() -> None:
    token = auth_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    type_names = read_type_names(CSV_PATH)
    if not type_names:
        fail("No types found in CSV")

    created = 0
    skipped = 0
    failed = 0

    for type_name in type_names:
        r = requests.post(
            f"{API_BASE}/item-types",
            headers=headers,
            json={"name": type_name, "description": None},
            timeout=TIMEOUT,
        )

        if r.status_code in (200, 201):
            created += 1
            print(f"OK  {type_name}")
        elif r.status_code == 409:
            skipped += 1
            print(f"SKIP {type_name} (already exists)")
        else:
            failed += 1
            print(f"ERR {type_name} -> {r.status_code} {r.text}")

    print(f"Done. created={created}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    main()
