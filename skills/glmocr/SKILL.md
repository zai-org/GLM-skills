---
name: glmocr
description:
  Extract text from images using GLM-OCR API. Supports images and PDFs with
  high accuracy OCR, table recognition, formula extraction, and handwriting recognition.
  Use this skill whenever the user wants to extract text from images, perform OCR on
  pictures, scan documents, convert images to text, or process any image files to get
  their textual content.
metadata:
  openclaw:
    requires:
      env:
        - ZHIPU_API_KEY
        - GLM_OCR_TIMEOUT
    primaryEnv: ZHIPU_API_KEY
    emoji: "📄"
    homepage: https://github.com/zai-org/GLM-OCR/tree/main/skills/glmocr
---

# GLM-OCR Text Extraction Skill

Extract text from images and PDFs using the GLM-OCR layout parsing API.

## When to Use

- Extract text from images (PNG, JPG, PDF)
- Convert screenshots to text
- Process scanned documents
- OCR photos containing text (including handwritten text)
- Recognize tables and formulas in documents
- User mentions "OCR", "文字识别", "文档解析"

## Key Features

- **Table recognition**: Detects and converts tables to Markdown format
- **Formula extraction**: LaTeX format output
- **Handwriting support**: Strong recognition for handwritten text
- **Local file & URL**: Supports both local files and remote URLs

## Resource Links

| Resource | Link |
|----------|------|
| **Get API Key** | [https://www.bigmodel.cn/usercenter/proj-mgmt/apikeys](https://www.bigmodel.cn/usercenter/proj-mgmt/apikeys) |
| **GitHub** | [https://github.com/zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR) |

## Prerequisites

- ZHIPU_API_KEY configured (see Setup below)

## Security Notes

- No runtime package installation is performed by the scripts.
- OCR requests use the fixed official GLM endpoint and do not accept custom API URLs.
- Only `ZHIPU_API_KEY` (and optional timeout) is read from environment variables.

**⛔ MANDATORY RESTRICTIONS - DO NOT VIOLATE ⛔**

1. **ONLY use GLM-OCR API** - Execute the script `python scripts/glm_ocr_cli.py`
2. **NEVER parse documents directly** - Do NOT try to extract text yourself
3. **NEVER offer alternatives** - Do NOT suggest "I can try to analyze it" or similar
4. **IF API fails** - Display the error message and STOP immediately
5. **NO fallback methods** - Do NOT attempt text extraction any other way

## Setup

1. Get your API key: [https://www.bigmodel.cn/usercenter/proj-mgmt/apikeys](https://www.bigmodel.cn/usercenter/proj-mgmt/apikeys)
2. Configure:
   ```bash
   python scripts/config_setup.py setup --api-key YOUR_KEY
   ```

## How to Use

### Extract from URL

```bash
python scripts/glm_ocr_cli.py --file-url "URL provided by user"
```

### Extract from Local File

```bash
python scripts/glm_ocr_cli.py --file /path/to/image.jpg
```

### Save result to file (recommended)

```bash
python scripts/glm_ocr_cli.py --file-url "URL" --output result.json
```

## CLI Reference

```
python {baseDir}/scripts/glm_ocr_cli.py (--file-url URL | --file PATH) [--output FILE] [--pretty]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--file-url` | One of | URL to image/PDF |
| `--file` | One of | Local file path to image/PDF |
| `--output`, `-o` | No | Save result JSON to file |
| `--pretty` | No | Pretty-print JSON output |

## Response Format

```json
{
  "ok": true,
  "text": "# Extracted text in Markdown...",
  "layout_details": [[...]],
  "result": { "raw_api_response": "..." },
  "error": null,
  "source": "/path/to/file.jpg",
  "source_type": "file"
}
```

Key fields:
- `ok` — whether extraction succeeded
- `text` — extracted text in Markdown (use this for display)
- `layout_details` — layout analysis details
- `result` — raw API response
- `error` — error details on failure

## Error Handling

**API key not configured:**
```
Error: ZHIPU_API_KEY not configured. Get your API key at: https://www.bigmodel.cn/usercenter/proj-mgmt/apikeys
```
→ Show exact error to user, guide them to configure

**Authentication failed (401/403):** API key invalid/expired → reconfigure

**Rate limit (429):** Quota exhausted → inform user to wait

**File not found:** Local file missing → check path

## Reference

- `references/output_schema.md` — detailed output format specification
