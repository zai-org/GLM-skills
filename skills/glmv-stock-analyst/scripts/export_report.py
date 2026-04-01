#!/usr/bin/env python3
"""
export_report.py — 将 Markdown 报告导出为 PDF 或 DOCX（图片嵌入，格式保留）

使用方式：
  python3 export_report.py report.md --format pdf
  python3 export_report.py report.md --format docx
  python3 export_report.py report.md --format both
  python3 export_report.py report.md --format pdf --output ~/Downloads/腾讯分析.pdf

依赖：
  pip3 install fpdf2 python-docx Pillow
"""

import argparse
import os
import re
import sys

# ═══════════════════════════════════════════════
# Markdown 解析
# ═══════════════════════════════════════════════


def parse_markdown(md_text):
    """将 Markdown 文本解析为结构化元素列表"""
    elements = []
    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # 空行
        if not line.strip():
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            elements.append(
                {"type": "heading", "level": level, "text": m.group(2).strip()}
            )
            i += 1
            continue

        # 水平分割线
        if re.match(r"^[-=─═]{3,}", line.strip()) or line.strip() == "---":
            elements.append({"type": "hr"})
            i += 1
            continue

        # 图片
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)", line)
        if m:
            elements.append({"type": "image", "alt": m.group(1), "path": m.group(2)})
            i += 1
            continue

        # 表格（连续的 | 行）
        if "|" in line and line.strip().startswith("|"):
            table_lines = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                table_lines.append(lines[i])
                i += 1
            # 解析表格
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                # 跳过分隔行 (---|---|---)
                if all(re.match(r"^[-:]+$", c) for c in cells if c):
                    continue
                rows.append(cells)
            if rows:
                elements.append({"type": "table", "rows": rows})
            continue

        # 引用块
        if line.startswith(">"):
            text = line.lstrip("> ").strip()
            elements.append({"type": "blockquote", "text": text})
            i += 1
            continue

        # 列表项（- xxx / * xxx / 1. xxx）
        if re.match(r"^[\-\*]\s+|^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[\-\*]\s+|^\d+\.\s+", lines[i]):
                item_text = re.sub(r"^[\-\*]\s+|^\d+\.\s+", "", lines[i]).strip()
                items.append(item_text)
                i += 1
            elements.append({"type": "list", "items": items})
            continue

        # 普通段落（合并连续非空行）
        para_lines = []
        while (
            i < len(lines)
            and lines[i].strip()
            and not re.match(r"^[#|>!\-\*=─═]", lines[i])
            and not re.match(r"^\d+\.\s+", lines[i])
        ):
            # 检查下一行是否是图片
            if re.match(r"^!\[", lines[i]):
                break
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            elements.append({"type": "paragraph", "text": "\n".join(para_lines)})
            continue

        i += 1

    return elements


# ═══════════════════════════════════════════════
# 中文字体检测
# ═══════════════════════════════════════════════


def find_cn_font():
    """查找系统中可用的中文字体文件"""
    candidates = [
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode MS.ttf",
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        # Windows
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


# ═══════════════════════════════════════════════
# 导出 PDF（fpdf2）
# ═══════════════════════════════════════════════


def export_pdf(elements, output_path, md_dir):
    """将解析后的元素导出为 PDF"""
    try:
        from fpdf import FPDF
    except ImportError:
        print("❌ fpdf2 未安装。请运行: pip3 install fpdf2", file=sys.stderr)
        return False

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # 注册中文字体
    font_path = find_cn_font()
    if font_path:
        try:
            pdf.add_font("CN", "", font_path, uni=True)
            pdf.add_font("CN", "B", font_path, uni=True)
            font_name = "CN"
        except Exception:
            font_name = "Helvetica"
    else:
        font_name = "Helvetica"

    def set_font(size=10, bold=False):
        style = "B" if bold else ""
        pdf.set_font(font_name, style, size)

    def clean_md(text):
        """去除 Markdown 格式标记，保留纯文本"""
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        return text

    def resolve_image(path):
        """解析图片路径（支持绝对路径和相对路径）"""
        if os.path.isabs(path) and os.path.exists(path):
            return path
        rel = os.path.join(md_dir, path)
        if os.path.exists(rel):
            return rel
        return None

    for elem in elements:
        t = elem["type"]

        if t == "heading":
            sizes = {1: 18, 2: 15, 3: 13, 4: 11}
            set_font(sizes.get(elem["level"], 11), bold=True)
            # 标题不能孤立在页底（至少留 30pt 给后续内容）
            if pdf.get_y() + 30 > pdf.h - pdf.b_margin:
                pdf.add_page()
            pdf.ln(4)
            pdf.multi_cell(0, 8, clean_md(elem["text"]))
            pdf.ln(2)

        elif t == "paragraph":
            set_font(10)
            pdf.multi_cell(0, 6, clean_md(elem["text"]))
            pdf.ln(3)

        elif t == "blockquote":
            set_font(9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, clean_md(elem["text"]))
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        elif t == "list":
            set_font(10)
            for item in elem["items"]:
                if pdf.get_y() + 8 > pdf.h - pdf.b_margin:
                    pdf.add_page()
                    set_font(10)
                pdf.set_x(pdf.l_margin)  # 重置X位置
                pdf.multi_cell(0, 6, f"    • {clean_md(item)}")
            pdf.ln(2)

        elif t == "hr":
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(5)

        elif t == "image":
            img_path = resolve_image(elem["path"])
            if img_path:
                try:
                    # 计算图片宽度（不超过页面宽度）
                    max_w = pdf.w - pdf.l_margin - pdf.r_margin
                    from PIL import Image as PILImage

                    with PILImage.open(img_path) as im:
                        w, h = im.size
                    # 按比例缩放
                    img_w = min(max_w, 170)
                    img_h = img_w * h / w
                    # 检查是否需要换页
                    if pdf.get_y() + img_h > pdf.h - pdf.b_margin:
                        pdf.add_page()
                    pdf.image(img_path, x=pdf.l_margin, w=img_w)
                    pdf.ln(3)
                except Exception as e:
                    set_font(8)
                    pdf.set_text_color(150, 150, 150)
                    pdf.multi_cell(0, 5, f"[图片: {elem['alt']}]")
                    pdf.set_text_color(0, 0, 0)
            else:
                set_font(8)
                pdf.set_text_color(150, 150, 150)
                pdf.multi_cell(0, 5, f"[图片未找到: {elem['alt']}]")
                pdf.set_text_color(0, 0, 0)

        elif t == "table":
            rows = elem["rows"]
            if not rows:
                continue
            n_cols = max(len(r) for r in rows)
            usable_w = pdf.w - pdf.l_margin - pdf.r_margin
            row_h = 7

            # 计算列宽：按内容长度分配
            col_max_len = [0] * n_cols
            for row in rows:
                for j, cell in enumerate(row):
                    if j < n_cols:
                        col_max_len[j] = max(col_max_len[j], len(clean_md(cell)))
            total_len = max(sum(col_max_len), 1)
            col_w = [max(usable_w * (l / total_len), 20) for l in col_max_len]
            # 归一化到 usable_w
            scale = usable_w / sum(col_w)
            col_w = [w * scale for w in col_w]

            # 预估表格总高度，不够就换页（表格 < 整页高度时才整体移）
            table_h = len(rows) * row_h + 5
            remaining = pdf.h - pdf.b_margin - pdf.get_y()
            if table_h < (pdf.h - pdf.t_margin - pdf.b_margin) and table_h > remaining:
                pdf.add_page()

            for row_idx, row in enumerate(rows):
                # 检查单行是否需要换页
                if pdf.get_y() + row_h > pdf.h - pdf.b_margin:
                    pdf.add_page()

                if row_idx == 0:
                    set_font(9, bold=True)
                    pdf.set_fill_color(240, 240, 240)
                    fill = True
                else:
                    set_font(9)
                    fill = False

                x_start = pdf.l_margin
                y_start = pdf.get_y()
                for j, cell in enumerate(row):
                    if j >= n_cols:
                        break
                    pdf.set_xy(x_start + sum(col_w[:j]), y_start)
                    text = clean_md(cell)
                    # 按列宽截断（每个字约占 2.5pt 宽度）
                    max_chars = max(int(col_w[j] / 2.5), 5)
                    if len(text) > max_chars:
                        text = text[: max_chars - 1] + "…"
                    pdf.cell(col_w[j], row_h, text, border=1, align="L", fill=fill)
                pdf.ln(row_h)

            pdf.ln(3)

    try:
        pdf.output(output_path)
        return True
    except Exception as e:
        print(f"❌ PDF 生成失败: {e}", file=sys.stderr)
        return False


# ═══════════════════════════════════════════════
# 导出 DOCX（python-docx）
# ═══════════════════════════════════════════════


def export_docx(elements, output_path, md_dir):
    """将解析后的元素导出为 DOCX"""
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Inches, Pt, RGBColor
    except ImportError:
        print(
            "❌ python-docx 未安装。请运行: pip3 install python-docx", file=sys.stderr
        )
        return False

    doc = Document()

    # 设置默认字体
    style = doc.styles["Normal"]
    style.font.size = Pt(10)

    def clean_md(text):
        """去除 Markdown 格式标记"""
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        return text

    def add_formatted_paragraph(text, style_name="Normal"):
        """添加段落，处理 **加粗** 格式和换行"""
        p = doc.add_paragraph(style=style_name)
        text_lines = text.split("\n")
        for li, line_text in enumerate(text_lines):
            parts = re.split(r"(\*\*[^*]+\*\*)", line_text)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    run = p.add_run(part[2:-2])
                    run.bold = True
                else:
                    cleaned = re.sub(r"`(.+?)`", r"\1", part)
                    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
                    p.add_run(cleaned)
            # 行间加换行（最后一行不加）
            if li < len(text_lines) - 1:
                p.add_run().add_break()
        return p

    def resolve_image(path):
        if os.path.isabs(path) and os.path.exists(path):
            return path
        rel = os.path.join(md_dir, path)
        if os.path.exists(rel):
            return rel
        return None

    for elem in elements:
        t = elem["type"]

        if t == "heading":
            level = min(elem["level"], 4)
            doc.add_heading(clean_md(elem["text"]), level=level)

        elif t == "paragraph":
            add_formatted_paragraph(elem["text"])

        elif t == "blockquote":
            p = doc.add_paragraph(clean_md(elem["text"]))
            p.paragraph_format.left_indent = Inches(0.3)
            for run in p.runs:
                run.font.color.rgb = RGBColor(100, 100, 100)
                run.font.size = Pt(9)

        elif t == "list":
            for item in elem["items"]:
                p = doc.add_paragraph(clean_md(item), style="List Bullet")

        elif t == "hr":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run("─" * 60)
            run.font.color.rgb = RGBColor(180, 180, 180)
            run.font.size = Pt(8)

        elif t == "image":
            img_path = resolve_image(elem["path"])
            if img_path:
                try:
                    doc.add_picture(img_path, width=Inches(5.5))
                    # 图片居中
                    last_paragraph = doc.paragraphs[-1]
                    last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception:
                    p = doc.add_paragraph(f"[图片: {elem['alt']}]")
                    p.runs[0].font.color.rgb = RGBColor(150, 150, 150)
            else:
                p = doc.add_paragraph(f"[图片未找到: {elem['alt']}]")
                p.runs[0].font.color.rgb = RGBColor(150, 150, 150)

        elif t == "table":
            rows = elem["rows"]
            if not rows:
                continue
            n_cols = max(len(r) for r in rows)
            table = doc.add_table(rows=len(rows), cols=n_cols)
            table.style = "Light Grid Accent 1"
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    if j < n_cols:
                        table.cell(i, j).text = clean_md(cell)
                        # 表头加粗
                        if i == 0:
                            for p in table.cell(i, j).paragraphs:
                                for run in p.runs:
                                    run.bold = True

    try:
        doc.save(output_path)
        return True
    except Exception as e:
        print(f"❌ DOCX 生成失败: {e}", file=sys.stderr)
        return False


# ═══════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="将 Markdown 股票分析报告导出为 PDF 或 DOCX",
        epilog="示例：\n"
        "  python3 export_report.py report.md --format pdf\n"
        "  python3 export_report.py report.md --format docx\n"
        "  python3 export_report.py report.md --format both\n"
        "  python3 export_report.py report.md --format pdf --output ~/Downloads/报告.pdf\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="输入的 Markdown 文件路径")
    parser.add_argument(
        "--format",
        choices=["pdf", "docx", "both"],
        default="pdf",
        help="输出格式 (默认: pdf)",
    )
    parser.add_argument(
        "--output", default=None, help="输出文件路径（不指定则自动命名）"
    )
    args = parser.parse_args()

    # 读取 Markdown
    if not os.path.exists(args.input):
        print(f"❌ 文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        md_text = f.read()

    md_dir = os.path.dirname(os.path.abspath(args.input))
    base_name = os.path.splitext(os.path.basename(args.input))[0]

    # 解析
    print(f"📄 解析 Markdown: {args.input}", file=sys.stderr)
    elements = parse_markdown(md_text)
    n_img = sum(1 for e in elements if e["type"] == "image")
    n_tbl = sum(1 for e in elements if e["type"] == "table")
    print(f"   {len(elements)} 个元素，{n_img} 张图片，{n_tbl} 个表格", file=sys.stderr)

    # 导出
    formats = [args.format] if args.format != "both" else ["pdf", "docx"]

    for fmt in formats:
        if args.output and len(formats) == 1:
            out_path = args.output
        else:
            out_path = os.path.join(md_dir, f"{base_name}.{fmt}")

        print(f"📝 导出 {fmt.upper()}: {out_path}", file=sys.stderr)

        if fmt == "pdf":
            ok = export_pdf(elements, out_path, md_dir)
        else:
            ok = export_docx(elements, out_path, md_dir)

        if ok:
            size_kb = os.path.getsize(out_path) // 1024
            print(f"   ✅ 成功! {size_kb}KB", file=sys.stderr)
        else:
            print(f"   ❌ 失败", file=sys.stderr)


if __name__ == "__main__":
    main()
