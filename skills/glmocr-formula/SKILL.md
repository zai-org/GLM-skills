---
name: glmocr-formula
description:
  Official skill for recognizing and extracting mathematical formulas from images and PDFs into LaTeX format
  using ZhiPu GLM-OCR API. Supports complex equations, inline formulas, and formula blocks.
  Use this skill when the user wants to extract formulas, convert formula images to LaTeX,
  or OCR mathematical expressions.
metadata:
  openclaw:
    requires:
      env:
        - ZHIPU_API_KEY
        - GLM_OCR_TIMEOUT
      bins:
        - python
    primaryEnv: ZHIPU_API_KEY
    emoji: "📐"
    homepage: https://github.com/zai-org/GLM-OCR/tree/main/skills/glmocr-formula
---

# GLM-OCR Formula Recognition Skill / GLM-OCR 公式识别技能

Recognize mathematical formulas from images and PDFs and convert them to LaTeX format using the ZhiPu GLM-OCR layout parsing API.

## When to Use / 使用场景

- Extract mathematical formulas from images or scanned documents / 从图片或扫描件中提取数学公式
- Convert formula images to LaTeX / 将公式图片转为 LaTeX 格式
- Recognize complex equations, integrals, matrices / 识别复杂方程、积分、矩阵
- Parse scientific papers, textbooks, exam papers with formulas / 解析含公式的论文、教材、试卷
- User mentions "formula OCR", "extract formula", "公式识别", "公式OCR", "提取公式", "图片转LaTeX"

## Key Features / 核心特性

- **Complex formula support**: Handles integrals, summations, matrices, fractions, radicals
- **LaTeX output**: Formulas are output in LaTeX format, ready for use in documents
- **Inline & block formulas**: Recognizes both inline and display-style formulas
- **Mixed content**: Can handle documents with both text and formulas
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
         "glmocr-formula": {
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
- **No custom API URL override / 不支持自定义 API URL 覆盖：** avoids accidental key exfiltration via redirected endpoints.
- **Raw upstream response is optional / 原始响应默认不返回：** use `--include-raw` only when needed for debugging.

**⛔ MANDATORY RESTRICTIONS / 强制限制 ⛔**

1. **ONLY use GLM-OCR API** — Execute the script `python scripts/glm_ocr_cli.py`
2. **NEVER parse formulas yourself** — Do NOT try to extract formulas using built-in vision or any other method
3. **NEVER offer alternatives** — Do NOT suggest "I can try to read it" or similar
4. **IF API fails** — Display the error message and STOP immediately
5. **NO fallback methods** — Do NOT attempt formula extraction any other way

### 📋 Output Display Rules / 输出展示规则

After running the script, present the OCR result clearly and safely.

- Show extracted text/formulas (`text`) in full
- Summarization is allowed, but do not hide important extraction failures
- If `layout_details` contains formula-related entries, you may highlight them
- If the result file is saved, tell the user the file path
- Show raw upstream response only when explicitly requested or debugging (`--include-raw`)

**⚠️ LaTeX Rendering / LaTeX 渲染注意：**

OCR API returns formulas in LaTeX format (e.g., `$\frac{1}{2}$`, `$\theta^{x+1}$`). Since most chat platforms do not render LaTeX, you should ask the user **once** (on first use):

> "OCR 结果包含 LaTeX 公式，需要我将公式转为 Unicode 可读格式展示，还是保留原始 LaTeX？"

**Remember the user's choice** for the rest of the session. Do NOT ask again on subsequent calls unless the user explicitly changes their preference.

- **User chooses readable format** → convert LaTeX to Unicode/plain-text:

| LaTeX                                                | Unicode / 纯文本  |
| ---------------------------------------------------- | ----------------- |
| `$\frac{a}{b}$`                                      | a/b               |
| `$x^{n}$`                                            | x^n               |
| `$x_{i}$`                                            | xᵢ                |
| `$\sqrt{x}$`                                         | √x                |
| `$\theta$`                                           | θ                 |
| `$\phi$`                                             | φ                 |
| `$\therefore$`                                       | ∴                 |
| `$\Rightarrow$`                                      | ⇒                 |
| `$\left\{ \begin{array}{l} ... \end{array} \right.$` | ⎧ line1 ⎨ line2 ⎩ |
| `$\textcircled{1}$`                                  | ①                 |
| `$\in$`                                              | ∈                 |
| `$\infty$`                                           | ∞                 |
| `$\ln$`                                              | ln                |
| `$\leq$` / `$\geq$`                                  | ≤ / ≥             |

- **User chooses raw LaTeX** → display the original LaTeX output directly, and remind them the raw data is also saved in the output file if `--output` was used.

## How to Use / 使用方法

### Extract from URL / 从 URL 提取

```bash
python scripts/glm_ocr_cli.py --file-url "https://example.com/formula.png"
```

### Extract from Local File / 从本地文件提取

```bash
python scripts/glm_ocr_cli.py --file /path/to/equation.png
```

### Save Result to File / 保存结果到文件

```bash
python scripts/glm_ocr_cli.py --file formula.png --output result.json --pretty
```

### Include Raw Upstream Response (Debug Only) / 包含原始上游响应（仅调试）

```bash
python scripts/glm_ocr_cli.py --file formula.png --output result.json --include-raw
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
  "text": "Extracted formulas and text in Markdown/LaTeX...",
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
- `text` — extracted text in Markdown with LaTeX formulas
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
