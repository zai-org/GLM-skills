# GLM Skills

Official skills for the [GLM](https://github.com/zai-org) family of models, designed for agent architectures including [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [OpenCode](https://github.com/opencode-ai/opencode), [OpenClaw](https://github.com/openclaw/openclaw), [AutoClaw](https://autoglm.zhipuai.cn/autoclaw/), and other AI coding agents.

This repository consolidates skills originally distributed across individual model repos into a single, unified collection.

## Skills

### GLM-V (Multimodal)

| Skill                                                   | Description                                                                   |
| ------------------------------------------------------- | ----------------------------------------------------------------------------- |
| [glmv-caption](skills/glmv-caption)                     | Generate captions and descriptions for images, videos, and documents          |
| [glmv-doc-based-writing](skills/glmv-doc-based-writing) | Write content (papers, articles, reports) based on PDF/DOCX documents         |
| [glmv-grounding](skills/glmv-grounding)                 | Object localization with bounding-box visualization in images and videos      |
| [glmv-pdf-to-ppt](skills/glmv-pdf-to-ppt)               | Convert PDF documents into multi-slide HTML presentations                     |
| [glmv-pdf-to-web](skills/glmv-pdf-to-web)               | Convert research papers into polished academic project websites               |
| [glmv-prd-to-app](skills/glmv-prd-to-app)               | Build full-stack web applications from PRD documents and prototypes           |
| [glmv-prompt-gen](skills/glmv-prompt-gen)               | Generate AI art prompts from visual references (Midjourney, SD, DALL-E, etc.) |
| [glmv-resume-screen](skills/glmv-resume-screen)         | Screen and evaluate resumes against user-defined criteria                     |
| [glmv-stock-analyst](skills/glmv-stock-analyst)         | Multi-source stock analysis and report generation for HK/A-share/US markets   |
| [glmv-web-replication](skills/glmv-web-replication)     | Create frontend visual replicas of existing websites                          |

### GLM-OCR

| Skill                                           | Description                                  |
| ----------------------------------------------- | -------------------------------------------- |
| [glmocr](skills/glmocr)                         | General text extraction from images and PDFs |
| [glmocr-formula](skills/glmocr-formula)         | Extract mathematical formulas into LaTeX     |
| [glmocr-handwriting](skills/glmocr-handwriting) | Recognize handwritten text                   |
| [glmocr-sdk](skills/glmocr-sdk)                 | Document parsing via GLM-OCR SDK CLI         |
| [glmocr-table](skills/glmocr-table)             | Extract tables into Markdown                 |

### GLM-Image

| Skill                                 | Description                                    |
| ------------------------------------- | ---------------------------------------------- |
| [glm-image-gen](skills/glm-image-gen) | Generate high-quality images from text prompts |

### Meta

| Skill                                       | Description                                         |
| ------------------------------------------- | --------------------------------------------------- |
| [glm-master-skill](skills/glm-master-skill) | Discovery and installation guide for all GLM skills |

## Installation

### Method 1: Install from Clawhub (Recommended)

```bash
# Install a single skill
npx clawhub@latest install glmocr

# Install multiple skills at once
npx clawhub@latest install glmocr glmocr-table glmv-caption glm-image-gen
```

### Method 2: Clone from GitHub

```bash
git clone https://github.com/zai-org/skills.git
# Then follow each skill's SKILL.md for setup instructions
```

## API Key

Most skills require a `ZHIPU_API_KEY` environment variable. Get your key at [bigmodel.cn](https://bigmodel.cn/usercenter/proj-mgmt/apikeys).

```bash
export ZHIPU_API_KEY="your_key"
```

## License

This project is licensed under the [Apache License 2.0](LICENSE).
