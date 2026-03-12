#!/usr/bin/env python3
import os
import sys
import time
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
CF_KV_NS_ID = os.environ.get("CF_KV_NAMESPACE_ID")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN")

if not all([CF_ACCOUNT_ID, CF_KV_NS_ID, CF_API_TOKEN]):
    print("ERROR: Missing required variables:")
    print("  CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID, CF_API_TOKEN")
    sys.exit(1)

KV_PUT_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
    f"/storage/kv/namespaces/{CF_KV_NS_ID}/values/drime_cookie"
)

MAX_RETRIES = 10
TIMEOUT_MS = 150000
INITIAL_DELAY = 5


def get_drime_cookie():
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)

                print(f"Attempt {attempt}/{MAX_RETRIES}: Opening dri.me ...")
                page.goto(
                    "https://dri.me/",
                    wait_until="domcontentloaded",
                    timeout=TIMEOUT_MS,
                )
                page.wait_for_timeout(5000)

                cookies = context.cookies()
                browser.close()

                cookie_str = "; ".join(
                    f"{c['name']}={c['value']}" for c in cookies if c["value"]
                )
                print(f"Cookie obtained: {len(cookie_str)} chars")
                return cookie_str

        except Exception as e:
            last_error = e
            delay = min(INITIAL_DELAY * (2 ** (attempt - 1)), 60)
            print(f"Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {delay}s...")
                time.sleep(delay)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")


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
        print("ERROR: Cookie too short.")
        sys.exit(1)

    push_to_kv(cookie)

    worker_url = os.environ.get("WORKER_URL")
    if worker_url:
        verify_worker(worker_url)

    print("Done!")
