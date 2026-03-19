from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"[contract-check] FAIL: {message}")
    raise SystemExit(1)


def assert_contains(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        fail(f"missing '{expected}' in {path}")


def assert_absent(path: Path) -> None:
    if path.exists():
        fail(f"path should not exist: {path}")


def main() -> int:
    main_py = ROOT / "apps" / "api" / "app" / "main.py"
    web_api_client = ROOT / "apps" / "web" / "lib" / "api.ts"

    assert_contains(main_py, '"/v1/chat/messages"')
    assert_contains(main_py, '"/v1/listings/search"')
    assert_contains(main_py, '"/v1/ingest/run"')
    assert_contains(main_py, 'status_code=410')

    assert_contains(web_api_client, "/v1/chat/messages")
    assert_contains(web_api_client, "/v1/listings/search")
    assert_contains(web_api_client, "/v1/leads")
    assert_contains(web_api_client, "/v1/auth/google/start")
    assert_contains(web_api_client, "/v1/auth/session")

    assert_absent(ROOT / "apps" / "web" / "app" / "api")
    assert_absent(ROOT / "apps" / "web" / "app" / "authorize")
    assert_absent(ROOT / "apps" / "web" / "app" / "debug")
    assert_absent(ROOT / "apps" / "web" / "app" / "pkce-test")
    assert_absent(ROOT / "apps" / "web" / "app" / "vertex-test")

    required_pages = [
        ROOT / "apps" / "web" / "app" / "dashboard",
        ROOT / "apps" / "web" / "app" / "login",
        ROOT / "apps" / "web" / "app" / "terms",
        ROOT / "apps" / "web" / "app" / "privacy",
        ROOT / "apps" / "web" / "app" / "contact",
    ]
    for page in required_pages:
        if not page.exists():
            fail(f"required page is missing: {page}")

    print("[contract-check] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
