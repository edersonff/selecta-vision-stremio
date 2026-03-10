#!/usr/bin/env python3
import os
import sys
import requests
from playwright.sync_api import sync_playwright

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
CF_KV_NS_ID = os.environ.get("CF_KV_NAMESPACE_ID")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN")
DRIME_HASH = os.environ.get("DRIME_HASH")

if not all([CF_ACCOUNT_ID, CF_KV_NS_ID, CF_API_TOKEN, DRIME_HASH]):
    print("ERROR: Missing required environment variables:")
    print("  CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID, CF_API_TOKEN, DRIME_HASH")
    sys.exit(1)

KV_PUT_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
    f"/storage/kv/namespaces/{CF_KV_NS_ID}/values/drime_cookie"
)


def get_drime_cookie():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        )
        page = context.new_page()

        print(f"Opening dri.me/{DRIME_HASH} ...")
        page.goto(
            f"https://dri.me/{DRIME_HASH}", wait_until="networkidle", timeout=30000
        )
        page.wait_for_timeout(3000)

        cookies = context.cookies()
        browser.close()

        cookie_str = "; ".join(
            f"{c['name']}={c['value']}" for c in cookies if c["value"]
        )
        print(f"Cookie obtained: {len(cookie_str)} chars")
        return cookie_str


def push_to_kv(cookie: str) -> None:
    resp = requests.put(
        KV_PUT_URL,
        headers={
            "Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "text/plain",
        },
        data=cookie,
        params={"expiration_ttl": 7200},
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise RuntimeError(f"KV put failed: {result}")
    print("Cookie saved to Cloudflare KV!")


def verify_worker(worker_url: str) -> None:
    resp = requests.get(f"{worker_url}/health", timeout=10)
    data = resp.json()
    print(f"Worker health: {data}")
    if not data.get("cookie_set"):
        raise RuntimeError("Worker reports cookie not set!")


if __name__ == "__main__":
    cookie = get_drime_cookie()
    if len(cookie) < 50:
        print("ERROR: Cookie too short, something went wrong.")
        sys.exit(1)

    push_to_kv(cookie)

    worker_url = os.environ.get("WORKER_URL")
    if worker_url:
        verify_worker(worker_url)

    print("Done!")
