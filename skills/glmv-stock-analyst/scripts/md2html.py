#!/usr/bin/env python3
"""
md2html.py — 将 Markdown 报告转换为带专业 CSS 的 HTML 页面
支持：表格、代码块、emoji、图片(file://)、文本折线图

用法:
  python3 md2html.py report.html < report.md
  python3 md2html.py -o report.html report.md
"""

import argparse
import os
import re
import sys

import markdown

# ═══════════════════════════════════════════════
# 专业报告 CSS 模板
# ═══════════════════════════════════════════════
CSS_TEMPLATE = """
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html{font-size:16px;}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",
             "Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif;
  line-height:1.85;color:#2c3e50;background:#f5f7fa;
}
.container{max-width:860px;margin:0 auto;padding:30px 24px;}

/* 标题 */
h1{
  font-size:1.6em;color:#1a1a2e;border-bottom:3px solid #3498db;
  padding-bottom:10px;margin-bottom:6px;font-weight:700;
}
h1 .meta{display:block;font-size:0.45em;color:#888;font-weight:400;margin-top:6px;}
h2{
  font-size:1.3em;color:#2980b9;margin-top:2em;margin-bottom:0.8em;
  padding-left:12px;border-left:4px solid #3498db;font-weight:700;
}
h3{font-size:1.1em;color:#34495e;margin-top:1.5em;margin-bottom:0.6em;font-weight:600;}

/* 段落 */
p{margin-bottom:0.9em;font-size:0.95em;text-align:justify;}

/* 表格 — 报告核心元素 */
table{
  width:100%;border-collapse:collapse;margin:1.2em 0;font-size:0.88em;
  border-radius:6px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);
}
thead{background:linear-gradient(135deg,#2980b9,#3498db);}
th{
  color:#fff;font-weight:600;padding:10px 14px;text-align:left;
  font-size:0.95em;letter-spacing:0.3px;
}
td{padding:9px 14px;border-bottom:1px solid #ecf0f1;color:#444;}
tbody tr:nth-child(even){background:#fafbfc;}
tbody tr:hover{background:#f0f7ff;}
tbody tr:last-child td{border-bottom:none;}

/* 列表 */
ul,ol{padding-left:1.6em;margin:0.8em 0;font-size:0.9em;line-height:1.75;}
li{margin-bottom:0.35em;}
li::marker{color:#3498db;}

/* 引用块（用于核心判断） */
blockquote{
  margin:1.2em 0;padding:14px 20px;background:linear-gradient(135deg,#fef9e7,#fdf2e9);
  border-left:4px solid #f39c12;border-radius:0 8px 8px 0;
  color:#7d6608;font-size:0.9em;line-height:1.7;
}
blockquote p:last-child{margin-bottom:0;}

/* 代码/折线图 */
code{
  background:#f1f3f5;padding:2px 6px;border-radius:4px;
  font-family:"SF Mono",Monaco,Consolas,monospace;font-size:0.85em;color:#e74c3c;
}
pre{
  background:#1e272e;color:#dcdcdc;border-radius:8px;padding:18px 20px;
  margin:1.2em 0;overflow-x:auto;font-size:0.82em;line-height:1.6;
  box-shadow:inset 0 1px 4px rgba(0,0,0,0.15);
}
pre code{background:none;padding:0;color:inherit;font-size:1em;}

/* 分隔线 */
hr{
  border:none;height:2px;background:linear-gradient(to right,
    transparent,#bdc3c7,transparent);margin:2.5em 0;
}

/* 图片 */
p > img{max-width:100%;height:auto;border-radius:8px;
  box-shadow:0 2px 12px rgba(0,0,0,0.1);margin:1em auto;display:block;}
figure{margin:1.5em 0;text-align:center;}
figure img{max-width:100%;height:auto;border-radius:8px;
  box-shadow:0 2px 12px rgba(0,0,0,0.1);}
figcaption{color:#888;font-size:0.82em;margin-top:8px;font-style:italic;}

/* 强调 */
strong{color:#1a1a2e;font-weight:600;}
em{color:#c0392b;}

/* 链接 */
a{color:#2980b9;text-decoration:none;border-bottom:1px dotted #2980b9;}
a:hover{color:#1abc9c;border-bottom-style:solid;}

/* 免责声明 */
.disclaimer{
  background:#ecf0f1;border-left:4px solid #95a5a6;
  padding:14px 18px;margin-top:2.5em;border-radius:0 8px 8px 0;
  color:#7f8c8d;font-size:0.82em;line-height:1.65;
}

/* 响应式 */
@media(max-width:640px){
  .container{padding:16px 12px;}
  h1{font-size:1.35em;}
  table{font-size:0.78em;}
  th,td{padding:7px 8px;}
}

/* 打印优化 */
@media print{
  body{background:#fff;color:#000;}
  .container{max-width:100%;padding:0;}
  table{page-break-inside:avoid;}
  h2{page-break-after:avoid;}
}
</style>
"""


def convert(md_text: str, title: str = "分析报告", base_dir: str = "") -> str:
    """将 Markdown 文本转为完整 HTML 页面"""

    # 处理图片相对路径 → 绝对 file:// 路径
    if base_dir:

        def _fix_img(m):
            alt = m.group(1)  # alt 文本
            src = m.group(2)  # 实际文件路径
            if src.startswith("http") or src.startswith("data:") or src.startswith("/"):
                return m.group(0)
            abs_path = os.path.abspath(os.path.join(base_dir, src))
            return f"![{alt}](file://{abs_path})"

        md_text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _fix_img, md_text)

    # Markdown 扩展
    md_ext = [
        "tables",  # 支持表格
        "fenced_code",  # 代码块 ```
        "nl2br",  # 换行
        "sane_lists",  # 规范列表
        # 'smart_strong',   # 非标准扩展，移除
    ]

    html_body = markdown.markdown(md_text, extensions=md_ext)

    # 提取 <h1> 作为页面标题（如果没有自定义标题）
    if not title or title == "分析报告":
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html_body)
        if m:
            import html as _h

            title = _h.unescape(re.sub(r"<[^>]+>", "", m.group(1)))

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
{CSS_TEMPLATE}
</head>
<body>
<div class="container">
{html_body}
</div>
</body>
</html>"""
    return full_html


def main():
    parser = argparse.ArgumentParser(description="Markdown → HTML (专业报告样式)")
    parser.add_argument("output", nargs="?", help="输出HTML路径")
    parser.add_argument("-o", "--out", help="输出HTML路径（等价于位置参数）")
    parser.add_argument("-i", "--input", help="输入MD文件（默认stdin）")
    parser.add_argument("--title", default="", help="页面标题")
    args = parser.parse_args()

    out_path = args.out or args.output
    if not out_path:
        print("用法: python3 md2html.py output.html < input.md", file=sys.stderr)
        print("      python3 md2html.py -o output.html input.md", file=sys.stderr)
        sys.exit(1)

    # 读取输入
    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            md_text = f.read()
    else:
        md_text = sys.stdin.read()

    if not md_text.strip():
        print("❌ 输入为空", file=sys.stderr)
        sys.exit(1)

    # 转换
    base_dir = os.path.dirname(os.path.abspath(args.input)) if args.input else ""
    result = convert(md_text, title=args.title, base_dir=base_dir)

    # 写入
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result)

    size_kb = len(result.encode("utf-8")) / 1024
    print(f"✅ {out_path} ({size_kb:.0f}KB)")


if __name__ == "__main__":
    main()
