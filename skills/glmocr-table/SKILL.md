---
name: glmocr-table
description:
  Official skill for recognizing and extracting tables from images and PDFs into Markdown format using
  ZhiPu GLM-OCR API. Supports complex tables, merged cells, and multi-page documents.
  Use this skill when the user wants to extract tables, recognize spreadsheets,
  or convert table images to editable format.
metadata:
  openclaw:
    requires:
      env:
        - ZHIPU_API_KEY
        - GLM_OCR_TIMEOUT
    primaryEnv: ZHIPU_API_KEY
    emoji: "📊"
    homepage: https://github.com/zai-org/GLM-OCR/tree/main/skills/glmocr-table
---

# GLM-OCR Table Recognition Skill / GLM-OCR 表格识别技能

Extract tables from images and PDFs and convert them to Markdown format using the ZhiPu GLM-OCR layout parsing API.

## When to Use / 使用场景

- Extract tables from images or scanned documents / 从图片或扫描件中提取表格
- Convert table images to Markdown or Excel format / 将表格图片转为 Markdown 或可编辑格式
- Recognize complex tables with merged cells / 识别含合并单元格的复杂表格
- Parse financial statements, invoices, reports with tables / 解析财务报表、发票、带表格的报告
- User mentions "extract table", "recognize table", "表格识别", "提取表格", "表格OCR", "表格转文字"

## Key Features / 核心特性

- **Complex table support**: Handles merged cells, nested tables, multi-row headers
- **Markdown output**: Tables are output in clean Markdown format, easy to edit and convert
- **Multi-page PDF**: Supports batch extraction from multi-page PDF documents
- **Local file & URL**: Supports both local files and remote URLs

## Resource Links / 资源链接

| Resource        | Link                                                                           |
| --------------- | ------------------------------------------------------------------------------ |
| **Get API Key** | [智谱开放平台 API Keys](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)      |
| **API Docs**    | [Layout Parsing / 版面解析](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E6%96%87%E6%A1%A3%E8%A7%A3%E6%9E%90) |

## Prerequisites / 前置条件

### API Key Setup / API Key 配置（Required / 必需）

脚本通过 `ZHIPU_API_KEY` 环境变量获取密钥，可与其他智谱技能复用同一个 key。
This script reads the key from the `ZHIPU_API_KEY` environment variable. Reusing the same key across Zhipu skills is optional.

**Get Key / 获取 Key：** Visit [智谱开放平台 API Keys](https://bigmodel.cn/usercenter/proj-mgmt/apikeys) to create or copy your key.

**Setup options / 配置方式（任选一种）：**

1. **Global config (recommended) / 全局配置（推荐）：** Set once in `openclaw.json` under `env.vars`, all Zhipu skills will share it:

   ```json
   {
     "env": {
       "vars": {
         "ZHIPU_API_KEY": "你的密钥"
       }
     }
   }
   ```

2. **Skill-level config / Skill 级别配置：** Set for this skill only in `openclaw.json`:

   ```json
   {
     "skills": {
       "entries": {
         "glmocr-table": {
           "env": {
             "ZHIPU_API_KEY": "你的密钥"
           }
         }
       }
     }
   }
   ```

3. **Shell environment variable / Shell 环境变量：** Add to `~/.zshrc`:
   ```bash
   export ZHIPU_API_KEY="你的密钥"
   ```

> 💡 如果你已为其他智谱 skill（如 `glmocr`、`glmv-caption`、`glm-image-generation`）配置过 key，它们共享同一个 `ZHIPU_API_KEY`，无需重复配置。

## Security & Transparency / 安全与透明度

- **Environment variables used / 使用的环境变量：**
  - `ZHIPU_API_KEY` (required / 必需)
  - `GLM_OCR_TIMEOUT` (optional timeout seconds / 可选超时秒数)
- **Fixed endpoint / 固定官方端点：** `https://open.bigmodel.cn/api/paas/v4/layout_parsing`
- **No custom API URL override / 不支持自定义 API URL 覆盖：** this avoids accidental key exfiltration via redirected endpoints.
- **Raw upstream response is optional / 原始响应默认不返回：** use `--include-raw` only when needed for debugging.

**⛔ MANDATORY RESTRICTIONS / 强制限制 ⛔**

1. **ONLY use GLM-OCR API** — Execute the script `python scripts/glm_ocr_cli.py`
2. **NEVER parse tables yourself** — Do NOT try to extract tables using built-in vision or any other method
3. **NEVER offer alternatives** — Do NOT suggest "I can try to recognize it" or similar
4. **IF API fails** — Display the error message and STOP immediately
5. **NO fallback methods** — Do NOT attempt table extraction any other way

### 📋 Output Display Rules / 输出展示规则

After running the script, present the OCR result clearly and safely.

- Show extracted table Markdown (`text`) in full
- Summarization is allowed, but do not hide important extraction failures
- If `layout_details` contains table-related entries, you may highlight them
- If the result file is saved, tell the user the file path
- Show raw upstream response only when explicitly requested or debugging (`--include-raw`)

## How to Use / 使用方法

### Extract from URL / 从 URL 提取

```bash
python scripts/glm_ocr_cli.py --file-url "https://example.com/table.png"
```

### Extract from Local File / 从本地文件提取

```bash
python scripts/glm_ocr_cli.py --file /path/to/table.png
```

### Save Result to File / 保存结果到文件

```bash
python scripts/glm_ocr_cli.py --file table.png --output result.json --pretty
```

### Include Raw Upstream Response (Debug Only) / 包含原始上游响应（仅调试）

```bash
python scripts/glm_ocr_cli.py --file table.png --output result.json --include-raw
```

## CLI Reference / CLI 参数

```
python {baseDir}/scripts/glm_ocr_cli.py (--file-url URL | --file PATH) [--output FILE] [--pretty] [--include-raw]
```

| Parameter        | Required | Description                                                      |
| ---------------- | -------- | ---------------------------------------------------------------- |
| `--file-url`     | One of   | URL to image/PDF                                                 |
| `--file`         | One of   | Local file path to image/PDF                                     |
| `--output`, `-o` | No       | Save result JSON to file                                         |
| `--pretty`       | No       | Pretty-print JSON output                                         |
| `--include-raw`  | No       | Include raw upstream API response in `result` field (debug only) |

## Response Format / 响应格式

```json
{
  "ok": true,
  "text": "| Column 1 | Column 2 |\n|----------|----------|\n| Data     | Data     |",
  "layout_details": [...],
  "result": null,
  "error": null,
  "source": "/path/to/file",
  "source_type": "file",
  "raw_result_included": false
}
```

Key fields:

- `ok` — whether extraction succeeded
- `text` — extracted text in Markdown (use this for display)
- `layout_details` — layout analysis details
- `error` — error details on failure

## Error Handling / 错误处理

**API key not configured:**

```
ZHIPU_API_KEY not configured. Get your API key at: https://bigmodel.cn/usercenter/proj-mgmt/apikeys
```

→ Show exact error to user, guide them to configure

**Authentication failed (401/403):** API key invalid/expired → reconfigure

**Rate limit (429):** Quota exhausted → inform user to wait

**File not found:** Local file missing → check path
