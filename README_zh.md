# GLM Skills

[GLM](https://github.com/zai-org) 系列模型的官方 Skills 合集，面向各类 Agent 架构，包括 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)、[OpenCode](https://github.com/opencode-ai/opencode)、[OpenClaw](https://github.com/openclaw/openclaw)、[AutoClaw](https://autoglm.zhipuai.cn/autoclaw/) 等 AI 编程助手。

本仓库将原本分散在各模型仓库中的 Skills 统一汇总管理。

## Skills 列表

### GLM-V（多模态）

| Skill | 说明 |
|-------|------|
| [glmv-caption](skills/glmv-caption) | 为图片、视频、文档生成描述和说明 |
| [glmv-doc-based-writing](skills/glmv-doc-based-writing) | 基于 PDF/DOCX 文档撰写论文、文章、报告等内容 |
| [glmv-grounding](skills/glmv-grounding) | 图像/视频中的目标定位与边界框可视化 |
| [glmv-pdf-to-ppt](skills/glmv-pdf-to-ppt) | 将 PDF 文档转换为多页 HTML 演示文稿 |
| [glmv-pdf-to-web](skills/glmv-pdf-to-web) | 将学术论文转换为精美的学术项目网页 |
| [glmv-prd-to-app](skills/glmv-prd-to-app) | 根据 PRD 文档和原型图构建全栈 Web 应用 |
| [glmv-prompt-gen](skills/glmv-prompt-gen) | 从视觉参考图生成 AI 绘画提示词（Midjourney、SD、DALL-E 等） |
| [glmv-resume-screen](skills/glmv-resume-screen) | 按自定义条件筛选和评估简历 |
| [glmv-web-replication](skills/glmv-web-replication) | 复刻现有网站的前端视觉呈现 |

### GLM-OCR

| Skill | 说明 |
|-------|------|
| [glmocr](skills/glmocr) | 通用图片/PDF 文字提取 |
| [glmocr-formula](skills/glmocr-formula) | 数学公式识别，输出 LaTeX 格式 |
| [glmocr-handwriting](skills/glmocr-handwriting) | 手写文字识别 |
| [glmocr-sdk](skills/glmocr-sdk) | 通过 GLM-OCR SDK CLI 解析文档 |
| [glmocr-table](skills/glmocr-table) | 表格提取，输出 Markdown 格式 |

### GLM-Image

| Skill | 说明 |
|-------|------|
| [glm-image-gen](skills/glm-image-gen) | 根据文本描述生成高质量图片 |

### 其他

| Skill | 说明 |
|-------|------|
| [glm-master-skill](skills/glm-master-skill) | GLM Skills 发现与安装指南 |

## 安装

### 方式一：通过 Clawhub 安装（推荐）

```bash
# 安装单个 Skill
npx clawhub@latest install glmocr

# 批量安装多个 Skill
npx clawhub@latest install glmocr glmocr-table glmv-caption glm-image-generation
```

### 方式二：从 GitHub 克隆

```bash
git clone https://github.com/zai-org/skills.git
# 然后按照各 Skill 的 SKILL.md 进行配置
```

## API Key

大部分 Skill 需要设置 `ZHIPU_API_KEY` 环境变量。在 [bigmodel.cn](https://bigmodel.cn/usercenter/proj-mgmt/apikeys) 获取 API Key。

```bash
export ZHIPU_API_KEY="your_key"
```

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 许可。
