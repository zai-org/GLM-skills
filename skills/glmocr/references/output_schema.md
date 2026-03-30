# GLM-Doc-Parser Output Schema

This document describes the output format returned by the GLM-OCR API wrapper.

## API Response Envelope

The `extract_text()` function returns a standardized response envelope:

```json
{
  "ok": true,
  "text": "Extracted text content in Markdown format...",
  "layout_details": [...],
  "result": {
    "raw": "API response object"
  },
  "error": null,
  "source": "https://example.com/image.jpg",
  "source_type": "url"
}
```

## Fields

### `ok` (boolean)
- Indicates whether the OCR operation was successful
- `true`: Extraction completed successfully
- `false`: An error occurred

### `text` (string)
- The extracted text content from the image in Markdown format
- Only present when `ok` is `true`
- Contains the full text extracted from the image/PDF
- Tables are formatted as Markdown tables
- Formulas are formatted as LaTeX

### `layout_details` (array | null)
- Layout analysis results from the GLM-OCR API
- Only present when `ok` is `true`
- Contains detailed information about detected elements:
  - Tables with cell positions
  - Formulas with positions
  - Text blocks with layout information
- Only present when `need_layout_visualization` is enabled in the API request

### `result` (object | null)
- The raw API response from GLM-OCR
- Only present when `ok` is `true`
- Contains the complete API response for advanced use cases
- Includes fields like `md_results`, `layout_details`, `usage`, etc.

### `error` (object | null)
- Error details when operation fails
- Only present when `ok` is `false`
- Structure:
  ```json
  {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  }
  ```

### `source` (string)
- The original input source (URL)
- Always present

### `source_type` (string)
- Type of the input source
- Value: `"url"` or `"file"`

## Error Codes

| Code | Description |
|------|-------------|
| `CONFIG_ERROR` | API key or URL not configured |
| `INPUT_ERROR` | Invalid input (invalid URL, unsupported format, etc.) |
| `API_ERROR` | API request failed (network error, authentication, rate limit, etc.) |

## Raw API Response

The `result` field contains the raw GLM-OCR API response from the layout parsing endpoint:

```json
{
  "md_results": "Extracted text content in Markdown format...",
  "layout_details": [
    {
      "type": "table",
      "bbox": [x1, y1, x2, y2],
      "cells": [...]
    },
    {
      "type": "formula",
      "bbox": [x1, y1, x2, y2],
      "text": "LaTeX formula..."
    }
  ],
  "usage": {
    "prompt_tokens": 1000,
    "completion_tokens": 500,
    "total_tokens": 1500
  }
}
```

The raw response structure follows the GLM-OCR Layout Parsing API format and may include:
- `md_results`: Markdown formatted text extraction results
- `layout_details`: Detailed layout analysis with bounding boxes and element classifications
- `usage`: Token usage statistics

## Usage Examples

### Basic Text Extraction

```python
from glm_ocr_cli import extract_text

result = extract_text("https://example.com/image.jpg")

if result["ok"]:
    print(result["text"])
else:
    print(f"Error: {result['error']['message']}")
```

### Accessing Raw API Response

```python
result = extract_text("https://example.com/image.jpg")

if result["ok"]:
    raw_response = result["result"]
    usage = raw_response.get("usage", {})
    print(f"Tokens used: {usage.get('total_tokens', 0)}")
```

### URL Processing

```python
result = extract_text("https://example.com/document.jpg")

if result["ok"]:
    print(f"Source type: {result['source_type']}")
    print(f"Text: {result['text']}")
```
