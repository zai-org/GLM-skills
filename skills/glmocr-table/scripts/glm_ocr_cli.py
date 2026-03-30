#!/usr/bin/env python3
"""
GLM-OCR CLI

Command-line interface for GLM-OCR vision model.

Usage:
    python scripts/glm_ocr_cli.py --file-url "URL"
    python scripts/glm_ocr_cli.py --file-url "URL" --pretty
"""

import argparse
import base64
import io
import json
import logging
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests  # noqa: E402
except ImportError:
    print(
        "Error: 'requests' is required. Please install it:\n"
        "  pip install requests\n"
        "Or install all dependencies: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_TIMEOUT = 60  # seconds
API_GUIDE_URL = "https://open.bigmodel.cn/usercenter/apikeys"
OFFICIAL_API_URL = "https://open.bigmodel.cn/api/paas/v4/layout_parsing"

# =============================================================================
# Environment
# =============================================================================


def _get_env(key: str) -> str:
    """Get an environment variable value."""
    return os.getenv(key, "").strip()


def get_config() -> tuple[str, str]:
    """
    Get API key from environment and use fixed official API URL.

    Returns:
        tuple of (api_url, api_key)

    Raises:
        ValueError: If not configured
    """
    api_key = _get_env("ZHIPU_API_KEY")

    if not api_key:
        raise ValueError(
            f"ZHIPU_API_KEY not configured. Get your API key at: {API_GUIDE_URL}"
        )

    # Security: fixed official endpoint (no custom URL override).
    return OFFICIAL_API_URL, api_key


# =============================================================================
# File Utilities
# =============================================================================


def _is_url(path: str) -> bool:
    """Check if the given path is a URL."""
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc]) and result.scheme in (
            "http",
            "https",
        )
    except Exception:
        return False


def _encode_file(file_path: str) -> tuple[str, str]:
    """
    Encode a local file to base64 data URI.

    Returns:
        tuple of (data_uri, error_message)
        On success, error_message is empty.
    """
    path = Path(file_path)
    if not path.exists():
        return "", f"File not found: {file_path}"
    if not path.is_file():
        return "", f"Not a regular file: {file_path}"

    # Guess MIME type, fallback to application/octet-stream
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "application/octet-stream"

    try:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}", ""
    except Exception as e:
        return "", f"Failed to read file: {e}"


# =============================================================================
# API Request
# =============================================================================


def _make_api_request(api_url: str, api_key: str, payload: dict) -> dict:
    """
    Make GLM-OCR API request.

    Args:
        api_url: API endpoint URL
        api_key: API key
        payload: Request payload

    Returns:
        API response dict

    Raises:
        RuntimeError: On API errors
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    timeout = float(os.getenv("GLM_OCR_TIMEOUT", str(DEFAULT_TIMEOUT)))

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    except requests.Timeout:
        raise RuntimeError(f"API request timed out after {timeout}s")
    except requests.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")

    # Handle HTTP errors
    if resp.status_code != 200:
        error_detail = ""
        try:
            error_body = resp.json()
            if isinstance(error_body, dict):
                error_detail = str(
                    error_body.get("error", {}).get("message", "")
                ).strip()
        except Exception:
            pass

        if not error_detail:
            error_detail = (resp.text[:200] or "No response body").strip()

        if resp.status_code == 401 or resp.status_code == 403:
            raise RuntimeError(
                f"Authentication failed ({resp.status_code}): {error_detail}"
            )
        elif resp.status_code == 429:
            raise RuntimeError(f"API rate limit exceeded (429): {error_detail}")
        elif resp.status_code >= 500:
            raise RuntimeError(
                f"API service error ({resp.status_code}): {error_detail}"
            )
        else:
            raise RuntimeError(f"API error ({resp.status_code}): {error_detail}")

    # Parse response
    try:
        result = resp.json()
    except Exception:
        raise RuntimeError(f"Invalid JSON response: {resp.text[:200]}")

    # Check API-level error
    if "error" in result:
        raise RuntimeError(f"API error: {result['error']}")

    return result


# =============================================================================
# Main API
# =============================================================================


def extract_text(
    image_source: str,
    model: str = "glm-ocr",
    include_raw_result: bool = False,
    **options,
) -> dict[str, Any]:
    """
    Extract text from image or PDF using GLM-OCR layout parsing API.

    Args:
        image_source: URL or local file path to the image/PDF
        model: Model to use (glm-ocr, etc.)
        **options: Additional API options:
            - return_crop_images: bool - Whether to return cropped images (default: False)
            - need_layout_visualization: bool - Whether to need layout visualization
            - start_page_id: int - Start page ID for PDF
            - end_page_id: int - End page ID for PDF

    Returns:
        {
            "ok": True,
            "text": "OCR extracted text (md_results)...",
            "layout_details": [...],  # Layout analysis results
            "result": { raw API result } or null,
            "error": None,
            "source": "original source",
            "source_type": "url" or "file"
        }
        or on error:
        {
            "ok": False,
            "text": "",
            "layout_details": None,
            "result": None,
            "error": {"code": "...", "message": "..."},
            "source": "original source",
            "source_type": "url" or "file"
        }
    """
    # Get config
    try:
        api_url, api_key = get_config()
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e), image_source)

    # Determine if URL or local file
    is_url = _is_url(image_source)
    if is_url:
        file_payload = image_source
    else:
        file_payload, encode_err = _encode_file(image_source)
        if encode_err:
            return _error("INPUT_ERROR", encode_err, image_source)

    # Build request payload
    payload = {
        "model": model,
        "file": file_payload,
        "return_crop_images": options.get("return_crop_images", False),
        "need_layout_visualization": options.get("need_layout_visualization", False),
        "start_page_id": options.get("start_page_id", 1),
        "end_page_id": options.get("end_page_id", 2),
    }

    # Call API
    try:
        result = _make_api_request(api_url, api_key, payload)
    except RuntimeError as e:
        return _error("API_ERROR", str(e), image_source)

    # Extract text from response
    try:
        extracted_text = _extract_text(result)
    except ValueError as e:
        return _error("API_ERROR", str(e), image_source)

    # Extract layout details
    layout_details = result.get("layout_details")

    return {
        "ok": True,
        "text": extracted_text,
        "layout_details": layout_details,
        "result": result if include_raw_result else None,
        "error": None,
        "source": image_source,
        "source_type": "url" if is_url else "file",
        "raw_result_included": include_raw_result,
    }


def _extract_text(result) -> str:
    """Extract text from GLM-OCR layout parsing API response."""
    if not isinstance(result, dict):
        raise ValueError("Invalid response schema: response must be an object")

    # Format 1: Layout parsing API response (md_results field)
    if "md_results" in result:
        md_results = result["md_results"]
        if isinstance(md_results, str):
            return md_results

    # Format 2: Nested data field
    if "data" in result and isinstance(result["data"], dict):
        data = result["data"]
        if "md_results" in data and isinstance(data["md_results"], str):
            return data["md_results"]

    raise ValueError(
        f"Invalid response schema: unable to extract text from {list(result.keys())}"
    )


def _error(code: str, message: str, source: str) -> dict:
    """Create error response."""
    return {
        "ok": False,
        "text": "",
        "layout_details": None,
        "result": None,
        "error": {"code": code, "message": message},
        "source": source,
        "source_type": "url" if _is_url(source) else "file",
        "raw_result_included": False,
    }


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="GLM-OCR - Extract text from images and PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from URL
  python scripts/glm_ocr_cli.py --file-url "https://example.com/image.jpg"

  # Extract from local file
  python scripts/glm_ocr_cli.py --file /path/to/image.jpg

  # Save result to file
  python scripts/glm_ocr_cli.py --file photo.png --output result.json --pretty

Configuration:
    Set env var: ZHIPU_API_KEY
  Get your key: https://bigmodel.cn/usercenter/proj-mgmt/apikeys
        """,
    )

    # Input (one of --file-url or --file required)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file-url", help="URL to image/PDF")
    input_group.add_argument("--file", help="Path to local image/PDF file")

    # Output options
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    parser.add_argument(
        "--output", "-o", metavar="FILE", help="Save result to JSON file"
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include raw upstream API response in output JSON (off by default)",
    )

    args = parser.parse_args()

    # Determine source
    source = args.file_url or args.file

    # Extract text
    result = extract_text(image_source=source, include_raw_result=args.include_raw)

    # Format output
    indent = 2 if args.pretty else None
    json_output = json.dumps(result, indent=indent, ensure_ascii=False)

    # Save to file or print
    if args.output:
        try:
            output_path = Path(args.output).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_output, encoding="utf-8")
            print(f"Result saved to: {output_path}", file=sys.stderr)
        except (PermissionError, OSError) as e:
            print(f"Error: Cannot write to {args.output}: {e}", file=sys.stderr)
            sys.exit(5)
    else:
        print(json_output)
        if result["ok"]:
            print("Tip: Use --output result.json to save the result", file=sys.stderr)

    # Exit code based on result
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
