#!/usr/bin/env python3
"""Render a web page to a PNG screenshot using Playwright.

Usage:
    python render_page.py --url URL --output OUTPUT_PNG [--width WIDTH] [--wait SECONDS]

Arguments:
    --url        URL to render (e.g., http://localhost:3000)
    --output     Path for the output PNG screenshot
    --width      Viewport width in pixels (default: 1280)
    --height     Viewport height in pixels (default: 800)
    --wait       Wait time in seconds after page load (default: 2)
    --full-page  Capture full scrollable page (default: true)
    --selector   Wait for a CSS selector to be visible before screenshot
    --routes     Comma-separated list of routes to screenshot (e.g., /,/about,/products)

Examples:
    # Single page
    python render_page.py --url http://localhost:3000 --output screenshot.png

    # Multiple routes
    python render_page.py --url http://localhost:3000 --output ./screenshots/ \
        --routes /,/products,/about,/contact

Output:
    Saves PNG screenshot(s). For multiple routes, saves as route_name.png in output dir.
"""

import argparse
import sys
import time
import json
from pathlib import Path

def ensure_playwright():
    """Ensure playwright and browsers are installed."""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        print("Installing playwright...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        return True

def render_url(url: str, output_path: str, width: int = 1280, height: int = 800,
               wait: float = 2, full_page: bool = True, selector: str = None):
    """Render a URL to a PNG screenshot."""
    from playwright.sync_api import sync_playwright

    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"Warning: Page load issue for {url}: {e}")
            # Try domcontentloaded as fallback
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except:
                print(f"Error: Could not load {url}")
                browser.close()
                return None

        # Wait for optional selector
        if selector:
            try:
                page.wait_for_selector(selector, timeout=10000)
            except:
                print(f"Warning: Selector '{selector}' not found within timeout")

        # Additional wait for dynamic content
        page.wait_for_timeout(int(wait * 1000))

        # Take screenshot
        page.screenshot(path=str(output_file), full_page=full_page)
        browser.close()

    print(f"Screenshot saved: {output_file}")
    return str(output_file)


def render_multiple_routes(base_url: str, routes: list, output_dir: str,
                          width: int = 1280, height: int = 800, wait: float = 2):
    """Render multiple routes and save screenshots."""
    from playwright.sync_api import sync_playwright

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        for route in routes:
            route = route.strip()
            url = f"{base_url.rstrip('/')}{route}"

            # Generate filename from route
            if route == "/" or route == "":
                filename = "index.png"
            else:
                filename = route.strip("/").replace("/", "_") + ".png"

            output_path = out_dir / filename

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(int(wait * 1000))
                page.screenshot(path=str(output_path), full_page=True)
                results.append({"route": route, "url": url, "screenshot": str(output_path), "status": "ok"})
                print(f"OK: {route} -> {output_path}")
            except Exception as e:
                results.append({"route": route, "url": url, "screenshot": None, "status": f"error: {e}"})
                print(f"FAIL: {route} -> {e}")

        browser.close()

    # Print summary
    print("\n--- RENDER SUMMARY ---")
    print(json.dumps(results, indent=2))
    return results


def main():
    parser = argparse.ArgumentParser(description="Render web pages to PNG screenshots")
    parser.add_argument("--url", required=True, help="Base URL to render")
    parser.add_argument("--output", required=True, help="Output PNG path or directory (for multi-route)")
    parser.add_argument("--width", type=int, default=1280, help="Viewport width (default: 1280)")
    parser.add_argument("--height", type=int, default=800, help="Viewport height (default: 800)")
    parser.add_argument("--wait", type=float, default=2, help="Wait time in seconds after load (default: 2)")
    parser.add_argument("--full-page", action="store_true", default=True, help="Capture full page")
    parser.add_argument("--no-full-page", dest="full_page", action="store_false")
    parser.add_argument("--selector", help="Wait for this CSS selector before screenshot")
    parser.add_argument("--routes", help="Comma-separated routes to screenshot (e.g., /,/about,/products)")

    args = parser.parse_args()

    ensure_playwright()

    if args.routes:
        routes = args.routes.split(",")
        render_multiple_routes(args.url, routes, args.output, args.width, args.height, args.wait)
    else:
        render_url(args.url, args.output, args.width, args.height, args.wait, args.full_page, args.selector)


if __name__ == "__main__":
    main()
