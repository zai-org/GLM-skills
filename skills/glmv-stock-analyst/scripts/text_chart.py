#!/usr/bin/env python3
"""
文本折线图生成器 — 用于在 Webchat 等不支持图片的环境中展示股价走势
支持两种模式：
  1. Sparkline: ▁▂▃▅▇▅▃▂ （单行）
  2. Block chart: 多行 Unicode 块状图（更详细）
"""


def sparkline(data, min_val=None, max_val=None, width=40):
    """
    生成单行 sparkline 折线图。

    Args:
        data: 数值列表（如收盘价序列）
        min_val, max_val: 范围（自动计算为 None）
        width: 输出宽度（字符数）

    Returns:
        str: sparkline 字符串
    """
    if not data or len(data) < 2:
        return "▁" * (width or 20)

    n = len(data)
    if min_val is None:
        min_val = min(data)
    if max_val is None:
        max_val = max(data)

    span = max_val - min_val
    if span == 0:
        span = 1

    # 8 级 Unicode 块字符
    blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    result = []
    for i in range(n):
        idx = int((data[i] - min_val) / span * 7.999)
        result.append(blocks[max(0, min(7, idx))])

    return "".join(result)


def block_chart(
    data, labels=None, height=10, width=50, title="", show_min_max=True, color_up=True
):
    """
    生成多行 Unicode 块状折线图。

    Args:
        data: 数值列表
        labels: X 轴标签列表（日期等），与 data 等长
        height: 图表高度（行数）
        width: 数据点数量（会重采样）
        title: 标题
        show_min_max: 是否标注最高最低价
        color_up: 是否用颜色标记涨跌

    Returns:
        str: 多行图表字符串
    """
    if not data or len(data) < 2:
        return "(数据不足)"

    n = len(data)

    # 重采样到目标宽度
    if n > width:
        step = n / width
        sampled = []
        sampled_labels = []
        for i in range(width):
            idx = int(i * step)
            sampled.append(data[min(idx, n - 1)])
            if labels:
                sampled_labels.append(labels[min(idx, n - 1)])
        data = sampled
        if labels:
            labels = sampled_labels
    elif n < width:
        width = n

    min_val = min(data)
    max_val = max(data)
    span = max_val - min_val
    if span == 0:
        span = 1

    # 完整块字符集（8 级 + 上半/下半组合 = 25 级）
    # 这里用简化版：8 级
    full_blocks = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇"]

    lines = []

    # 标题
    if title:
        lines.append(f"  {title}")
        lines.append("")

    # Y轴范围标注
    y_labels = []
    for i in range(height):
        val = (
            max_val - (i / (height - 1)) * span
            if height > 1
            else (max_val + min_val) / 2
        )
        y_labels.append(f"{val:.1f}")

    max_label_len = max(len(l) for l in y_labels) if y_labels else 0

    # 绘制每一行
    for row in range(height):
        threshold = max_val - ((row + 0.5) / height) * span

        line_parts = [f"{y_labels[row]:>{max_label_len}} │"]

        for val in data:
            if val >= threshold:
                line_parts.append("█")
            else:
                line_parts.append(" ")

        lines.append("".join(line_parts))

    # X轴
    x_axis = " " * (max_label_len + 2) + "─" * width
    lines.append(x_axis)

    # X轴标签（精简显示首尾+均匀采样）
    if labels and len(labels) > 0:
        label_positions = [0]
        if len(labels) > 2:
            label_positions.append(len(labels) - 1)
            step = max(1, (len(labels) - 1) // 4)
            for i in range(step, len(labels) - 1, step):
                label_positions.append(i)
        label_positions = sorted(set(label_positions))

        label_line = [" " * (max_label_len + 2)]
        pos_idx = 0
        for i in range(len(labels)):
            if pos_idx < len(label_positions) and i == label_positions[pos_idx]:
                lbl = str(labels[i])[-8:]  # 截短标签
                label_line.append(lbl[:width])
                pos_idx += 1
            else:
                label_line.append(" ")
        lines.append("".join(label_line))

    # 最高/最低价标注
    if show_min_max:
        max_idx = data.index(max(data))
        min_idx = data.index(min(data))
        lines.append("")
        info = f"  最高: {max_val:.1f} | 最低: {min_val:.1f} | 振幅: {span:.1f} ({span/min_val*100:.1f}%)"
        lines.append(info)

    return "\n".join(lines)


def candlestick_text(kline_data, height=12, width=40, title=""):
    """
    从 OHLCV 数据生成文本 K 线图。

    Args:
        kline_data: [{"open":o,"high":h,"low":l,"close":c,"volume":v}, ...]
        height: 图表高度
        width: 显示的K线根数
        title: 标题

    Returns:
        str: 文本K线图
    """
    if not kline_data or len(kline_data) < 2:
        return "(K线数据不足)"

    # 取最近的 width 根 K 线
    data = kline_data[-width:] if len(kline_data) > width else kline_data
    n = len(data)

    # 找全局高低点
    global_low = min(d.get("low", d.get("close", 0)) for d in data)
    global_high = max(d.get("high", d.get("close", 0)) for d in data)
    span = global_high - global_low
    if span == 0:
        span = 1

    lines = []
    if title:
        lines.append(f"  {title}")
        lines.append("")

    price_range = global_high - global_low
    for row in range(height):
        price = (
            global_high - (row / (height - 1)) * price_range
            if height > 1
            else (global_high + global_low) / 2
        )

        line = f"{price:>9.1f} │"

        for d in data:
            o = d.get("open", d.get("close", 0))
            h = d.get("high", d.get("close", 0))
            l = d.get("low", d.get("close", 0))
            c = d.get("close", 0)

            if h >= price >= l:
                # 这根K线的范围覆盖当前价格行
                if o <= price <= c:
                    line += "█"  # 实体（阳线）
                elif c <= price <= o:
                    line += "▓"  # 实体（阴线）
                elif price >= max(o, c):
                    line += "│"  # 上影线
                elif price <= min(o, c):
                    line += "│"  # 下影线
                else:
                    line += "█"
            else:
                line += " "

        lines.append(line)

    # 底部
    lines.append(" " * 11 + "─" * n)

    # 阳线/阴线标记
    marker_line = " " * 11
    for d in data:
        c = d.get("close", 0)
        o = d.get("open", c)
        if c >= o:
            marker_line += "▲"
        else:
            marker_line += "▼"
    lines.append(marker_line)

    # 最新价
    last = data[-1]
    lc = last.get("close", 0)
    lo = last.get("open", lc)
    change = lc - lo
    pct = change / lo * 100 if lo != 0 else 0
    sign = "+" if change >= 0 else ""
    lines.append(f"  最新: {lc:.1f} ({sign}{change:.1f}, {sign}{pct:.1f}%)")

    return "\n".join(lines)


# ── 测试 ──
if __name__ == "__main__":
    # 模拟腾讯股价数据（60天）
    prices = [
        550,
        558,
        562,
        555,
        560,
        568,
        572,
        578,
        582,
        590,
        595,
        602,
        615,
        622,
        618,
        610,
        598,
        585,
        570,
        555,
        545,
        535,
        520,
        505,
        495,
        480,
        485,
        495,
        510,
        525,
        530,
        528,
        518,
        508,
        500,
        495,
        490,
        488,
        492,
        498,
        505,
        512,
        518,
        515,
        508,
        500,
        492,
        485,
        480,
        478,
        482,
        488,
        492,
        490,
        485,
        480,
        478,
        482,
        485,
        483,
    ]

    dates = [f"{'01' if i<10 else '11'}/{(i%30)+1:02d}" for i in range(len(prices))]

    print("=" * 60)
    print("测试 1: Sparkline（单行）")
    print("=" * 60)
    s = sparkline(prices[-30:])
    print(f"  近30日: {s}")
    print()

    print("=" * 60)
    print("测试 2: Block Chart（多行块状图）")
    print("=" * 60)
    print(
        block_chart(
            prices[-30:],
            labels=dates[-30:],
            height=10,
            width=40,
            title="腾讯控股(0700.HK) 近30日收盘价",
        )
    )
    print()

    print("=" * 60)
    print("测试 3: Candlestick Text（文本K线）")
    print("=" * 60)
    # 模拟 OHLCV 数据
    ohlcv = []
    base = 480
    for i, p in enumerate(prices[-20:]):
        rng = abs(p - base) * 0.03
        ohlcv.append(
            {
                "open": p - rng * (0.5 if i % 3 == 0 else -0.3),
                "high": p + rng,
                "low": p - rng * 1.2,
                "close": p,
                "volume": 1000000 + i * 50000,
            }
        )
    print(candlestick_text(ohlcv, height=10, title="腾讯控股(0700.HK) 近20日K线"))
