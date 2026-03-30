#!/usr/bin/env python3
"""Wait for a server to become available, then optionally check specific routes.

Usage:
    python wait_and_check.py --url URL [--timeout SECONDS] [--routes ROUTE...]

Arguments:
    --url       Base URL to check (e.g., http://localhost:3000)
    --timeout   Max wait time in seconds (default: 60)
    --routes    Additional routes to verify after server is up
    --interval  Check interval in seconds (default: 2)

Examples:
    python wait_and_check.py --url http://localhost:3000 --timeout 30
    python wait_and_check.py --url http://localhost:3000 --routes / /api/products /about
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error


def wait_for_server(url: str, timeout: int = 60, interval: int = 2) -> bool:
    """Wait for server to respond."""
    start = time.time()
    print(f"Waiting for {url} (timeout: {timeout}s)...")

    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"Server is UP (status: {resp.status}, took {time.time()-start:.1f}s)")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionError, OSError):
            time.sleep(interval)

    print(f"TIMEOUT: Server did not respond within {timeout}s")
    return False


def check_route(base_url: str, route: str) -> dict:
    """Check a single route."""
    url = f"{base_url.rstrip('/')}{route}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            content_type = resp.headers.get("Content-Type", "")
            return {
                "route": route,
                "status": resp.status,
                "content_type": content_type,
                "body_length": len(body),
                "is_html": "text/html" in content_type,
                "is_json": "application/json" in content_type,
                "ok": True,
            }
    except Exception as e:
        return {"route": route, "error": str(e), "ok": False}


def main():
    parser = argparse.ArgumentParser(description="Wait for server and check routes")
    parser.add_argument("--url", required=True, help="Base URL")
    parser.add_argument("--timeout", type=int, default=60, help="Wait timeout (seconds)")
    parser.add_argument("--interval", type=int, default=2, help="Check interval (seconds)")
    parser.add_argument("--routes", nargs="*", default=[], help="Routes to verify")

    args = parser.parse_args()

    if not wait_for_server(args.url, args.timeout, args.interval):
        sys.exit(1)

    if args.routes:
        print(f"\nChecking {len(args.routes)} routes...")
        results = []
        for route in args.routes:
            result = check_route(args.url, route)
            status = "OK" if result["ok"] else "FAIL"
            print(f"  [{status}] {route} -> {result.get('status', 'N/A')}")
            results.append(result)

        ok_count = sum(1 for r in results if r["ok"])
        print(f"\nRoutes: {ok_count}/{len(results)} passed")
        print(json.dumps(results, indent=2))

        if ok_count < len(results):
            sys.exit(1)


if __name__ == "__main__":
    main()
