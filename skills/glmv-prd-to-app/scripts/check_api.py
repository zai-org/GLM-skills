#!/usr/bin/env python3
"""Check API endpoints are responding correctly.

Usage:
    python check_api.py --base-url URL [--endpoints-file FILE] [--endpoints ENDPOINT...]

Arguments:
    --base-url        Base URL for API (e.g., http://localhost:3000/api)
    --endpoints-file  JSON file with endpoint definitions
    --endpoints       Space-separated list of endpoints to check (e.g., GET:/products POST:/users)
    --timeout         Request timeout in seconds (default: 10)
    --verbose         Show response bodies

Endpoints file format (endpoints.json):
    [
      {"method": "GET", "path": "/products", "expected_status": 200, "description": "List products"},
      {"method": "GET", "path": "/products/1", "expected_status": 200, "description": "Get product by ID"},
      {"method": "POST", "path": "/auth/login", "body": {"email": "test@test.com", "password": "123"}, "expected_status": 200}
    ]

Examples:
    python check_api.py --base-url http://localhost:3000/api --endpoints GET:/products GET:/users
    python check_api.py --base-url http://localhost:3000/api --endpoints-file endpoints.json --verbose
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def check_endpoint(base_url: str, method: str, path: str, body: dict = None,
                   expected_status: int = 200, timeout: int = 10, verbose: bool = False) -> dict:
    """Check a single API endpoint."""
    url = f"{base_url.rstrip('/')}{path}"
    result = {
        "method": method,
        "path": path,
        "url": url,
        "expected_status": expected_status,
    }

    try:
        if body:
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Content-Type", "application/json")
        else:
            req = urllib.request.Request(url, method=method)

        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp_body = resp.read().decode("utf-8", errors="replace")

            result["status"] = status
            result["passed"] = status == expected_status

            if verbose:
                try:
                    result["body"] = json.loads(resp_body)
                except json.JSONDecodeError:
                    result["body"] = resp_body[:500]

            # Check if response is valid JSON
            try:
                parsed = json.loads(resp_body)
                result["is_json"] = True
                if isinstance(parsed, list):
                    result["items_count"] = len(parsed)
                elif isinstance(parsed, dict):
                    result["keys"] = list(parsed.keys())[:10]
            except json.JSONDecodeError:
                result["is_json"] = False

    except urllib.error.HTTPError as e:
        result["status"] = e.code
        result["passed"] = e.code == expected_status
        result["error"] = str(e)
    except urllib.error.URLError as e:
        result["status"] = None
        result["passed"] = False
        result["error"] = f"Connection failed: {e.reason}"
    except Exception as e:
        result["status"] = None
        result["passed"] = False
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Check API endpoints")
    parser.add_argument("--base-url", required=True, help="Base URL for API")
    parser.add_argument("--endpoints-file", help="JSON file with endpoint definitions")
    parser.add_argument("--endpoints", nargs="*", help="Endpoints as METHOD:PATH (e.g., GET:/products)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="Show response bodies")

    args = parser.parse_args()

    endpoints = []

    # Load from file
    if args.endpoints_file:
        ep_file = Path(args.endpoints_file)
        if ep_file.exists():
            endpoints.extend(json.loads(ep_file.read_text(encoding="utf-8")))
        else:
            print(f"Warning: Endpoints file not found: {ep_file}")

    # Parse CLI endpoints
    if args.endpoints:
        for ep in args.endpoints:
            if ":" in ep:
                method, path = ep.split(":", 1)
                endpoints.append({"method": method.upper(), "path": path, "expected_status": 200})
            else:
                endpoints.append({"method": "GET", "path": ep, "expected_status": 200})

    if not endpoints:
        # Auto-discover common endpoints
        print("No endpoints specified. Trying common paths...")
        common_paths = [
            "/", "/api", "/api/health",
            "/api/products", "/api/users", "/api/categories",
            "/api/posts", "/api/items", "/api/orders",
        ]
        endpoints = [{"method": "GET", "path": p, "expected_status": 200} for p in common_paths]

    # Run checks
    results = []
    passed = 0
    failed = 0

    for ep in endpoints:
        result = check_endpoint(
            args.base_url,
            ep.get("method", "GET"),
            ep["path"],
            ep.get("body"),
            ep.get("expected_status", 200),
            args.timeout,
            args.verbose,
        )

        status_icon = "PASS" if result["passed"] else "FAIL"
        desc = ep.get("description", "")
        print(f"[{status_icon}] {result['method']} {result['path']} -> {result.get('status', 'N/A')} {desc}")

        if result.get("error"):
            print(f"       Error: {result['error']}")
        if result.get("items_count") is not None:
            print(f"       Items: {result['items_count']}")

        results.append(result)
        if result["passed"]:
            passed += 1
        else:
            failed += 1

    # Summary
    total = len(results)
    print(f"\n--- API CHECK SUMMARY ---")
    print(f"Total: {total}  Passed: {passed}  Failed: {failed}")
    print(json.dumps({"total": total, "passed": passed, "failed": failed, "results": results}, indent=2))

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
