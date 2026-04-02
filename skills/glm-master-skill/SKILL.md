---
name: glm-master-skill
description: |
  Documentation-only master skill for GLM ecosystem discovery and installation.
  This skill does not execute scripts or subprocess commands.
  It provides a curated list of official GLM skills, install methods, and source links.
metadata:
  openclaw:
    requires:
      env: []
      bins: []
    emoji: "🎯"
    source: https://github.com/zai-org/GLM-skills/tree/main/skills/glm-master-skill
    homepage: https://github.com/zai-org/GLM-skills/tree/main/skills/glm-master-skill
---

# GLM Master Skill (Guide Only) / GLM 技能总览（仅指南）

This is a **documentation-only** master skill.

- ✅ It **introduces** available GLM skills.
- ✅ It **provides official install links and commands**.
- ❌ It **does not run any local scripts**.
- ❌ It **does not use subprocess**.

本 Skill 只做导航与安装说明，不执行任何本地脚本。

---

## Official Skills Catalog / 官方技能目录

### GLM-OCR

| Skill                | Purpose                       | Link                                                                  |
| -------------------- | ----------------------------- | --------------------------------------------------------------------- |
| `glmocr`             | General OCR (text extraction) | https://github.com/zai-org/GLM-skills/tree/main/skills/glmocr             |
| `glmocr-table`       | Table extraction              | https://github.com/zai-org/GLM-skills/tree/main/skills/glmocr-table       |
| `glmocr-formula`     | Formula extraction            | https://github.com/zai-org/GLM-skills/tree/main/skills/glmocr-formula     |
| `glmocr-handwriting` | Handwriting OCR               | https://github.com/zai-org/GLM-skills/tree/main/skills/glmocr-handwriting |
| `glmocr-sdk`         | GLM-OCR SDK guidance          | https://github.com/zai-org/GLM-skills/tree/main/skills/glmocr-sdk         |

### GLM-Image

| Skill           | Purpose                  | Link                                                             |
| --------------- | ------------------------ | ---------------------------------------------------------------- |
| `glm-image-gen` | Text-to-image generation | https://github.com/zai-org/GLM-skills/tree/main/skills/glm-image-gen |

### GLM-V

| Skill                    | Purpose                                                      | Link                                                                      |
| ------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| `glmv-caption`           | Image/video/file captioning                                  | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-caption           |
| `glmv-prompt-gen`        | Prompt generation from visual input                          | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-prompt-gen        |
| `glmv-resume-screen`     | Resume screening                                             | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-resume-screen     |
| `glmv-grounding`         | Image/video target localization & bounding-box visualization | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-grounding         |
| `glmv-doc-based-writing` | Document-based content generation (PDF/DOCX)                 | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-doc-based-writing |
| `glmv-pdf-to-ppt`        | PDF to HTML presentation conversion                          | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-pdf-to-ppt        |
| `glmv-pdf-to-web`        | PDF to academic project website conversion                   | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-pdf-to-web        |
| `glmv-prd-to-app`        | Build full-stack web app from PRD documents & prototypes     | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-prd-to-app        |
| `glmv-stock-analyst`     | Multi-source stock analysis and report generation            | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-stock-analyst     |
| `glmv-web-replication`   | Frontend visual replication of public websites               | https://github.com/zai-org/GLM-skills/tree/main/skills/glmv-web-replication   |

---

## Installation Methods / 安装方式

### Method A: Install from Clawhub (Recommended first)

```bash
npx clawhub@latest install <skill-name>
```

Example:

```bash
npx clawhub@latest install glmocr
npx clawhub@latest install glmv-caption
npx clawhub@latest install glm-image-gen
```

You can also install multiple skills at once:

```bash
npx clawhub@latest install glmocr glmocr-table glmocr-formula glmocr-handwriting glmocr-sdk glm-image-gen glmv-caption glmv-prompt-gen glmv-resume-screen glmv-grounding glmv-doc-based-writing glmv-pdf-to-ppt glmv-pdf-to-web glmv-prd-to-app glmv-stock-analyst glmv-web-replication
```

### Method B: If Clawhub is rate-limited

You may see errors like:

```text
✖ Rate limit exceeded (retry in 47s, remaining: 0/20, reset in 47s)
```

Use one of the following:

1. Wait and retry after reset time.
2. Install from the official GitHub skill directory directly.

你可能会遇到 Clawhub 频率限制；可等待重试，或改用 GitHub 源安装。

### Method C: Install from GitHub source

Use each skill's official path (see catalog above).

General idea:

```bash
git clone https://github.com/zai-org/GLM-skills.git
```

Then follow that skill's own `SKILL.md` for exact setup steps.

---

## API Key Setup (required by most downstream skills)

Most GLM skills require the environment variable `ZHIPU_API_KEY`. This master skill itself does **not** read or use the key, but downstream skills will.

> **Security best practices:**
>
> - Create a **limited-scope** API key with only the permissions needed for the skills you plan to use.
> - Store the key in environment variables only — **never hardcode** it in source files or commit it to version control.
> - Add `ZHIPU_API_KEY` to your `.gitignore` if storing it in a `.env` file.
> - Rotate the key periodically and revoke unused keys at https://bigmodel.cn/usercenter/proj-mgmt/apikeys.

Get API key: https://bigmodel.cn/usercenter/proj-mgmt/apikeys

Set in shell:

```bash
export ZHIPU_API_KEY="your_key"
```

或者写入环境配置文件（如 `~/.zshrc`）以长期生效，但请确保该文件不会被提交到版本控制系统。

---

## How an Agent should use this Master Skill

When user asks for GLM OCR / GLM Image / GLM-V capabilities:

1. Match user intent to one or more skills in the catalog.
2. Recommend installation via `npx clawhub@latest install <skill-name>` first.
3. If rate-limited, tell user to retry later or use GitHub skill source.
4. Open the selected skill's official `SKILL.md` and follow its instructions.

当用户提出具体任务时，Agent 按上述流程引导安装并跳转到对应技能文档。

---

## Resource Links

- GLM-5: https://github.com/zai-org/GLM-5
- GLM-OCR: https://github.com/zai-org/GLM-OCR
- GLM-Image: https://github.com/zai-org/GLM-Image
- GLM-V: https://github.com/zai-org/GLM-V
- API Docs: https://docs.bigmodel.cn/
- API Key: https://bigmodel.cn/usercenter/proj-mgmt/apikeys

---

## Why this design / 设计原因

Some skill-sharing platforms may flag `subprocess` execution as high risk during review.

To keep this master skill safe and easy to pass review:

1. No helper `.py` installer.
2. No local command execution logic.
3. Only official links + clear installation instructions.

由于 `subprocess` 在审核中可能被视为高风险，这里采用“纯文档”方式。

---

## Security Note

This master skill intentionally avoids executable helper scripts.
It is designed for safer sharing/review in public skill marketplaces.

本 Skill 刻意不包含可执行安装脚本，以降低审核风险。
