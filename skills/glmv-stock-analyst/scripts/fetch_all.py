#!/usr/bin/env python3
"""
股票数据一键获取 + 图表生成 + 报告模板生成 v28.0

数据源三路冗余：akshare → 东方财富原始接口 → yfinance
输出：data.json + PNG 图表 + 数据摘要 JSON（供多模态主模型分析）

工作模式：
  脚本只负责数据采集和图表生成，不生成报告文本。
  主模型（如 glm-5v-turbo）读取 data.json 和图片后，自行输出分析报告。

用法: python3 fetch_all.py 0700.HK [--adr TCEHY]
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# 文本图表（Webchat 内嵌展示用）
try:
    from text_chart import block_chart, sparkline

    HAS_TEXT_CHART = True
except ImportError:
    HAS_TEXT_CHART = False

# ── 可选依赖，缺失不中断 ──
try:
    import akshare as ak

    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("  ⚠ akshare 未安装，跳过此数据源 (pip3 install akshare)")

try:
    import requests as _requests
    import yfinance as yf

    # 创建带 10 秒超时的 session，所有 yfinance 调用共用
    _yf_session = _requests.Session()
    _yf_session.headers["User-Agent"] = "Mozilla/5.0"
    _orig_request = _yf_session.request

    def _timeout_request(*args, **kwargs):
        kwargs.setdefault("timeout", 10)
        return _orig_request(*args, **kwargs)

    _yf_session.request = _timeout_request
    HAS_YFINANCE = True
    print(f"  ✅ yfinance（单次请求超时: 10秒）")
except ImportError:
    HAS_YFINANCE = False
    _yf_session = None
    print("  ⚠ yfinance 未安装，跳过此数据源")


def _yf(code):
    """创建带超时控制的 yfinance Ticker"""
    if _yf_session:
        return yf.Ticker(code, session=_yf_session)
    return yf.Ticker(code)


try:
    import tushare as ts

    _TS_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
    if _TS_TOKEN:
        ts.set_token(_TS_TOKEN)
        TS_PRO = ts.pro_api()
        HAS_TUSHARE = True
        print(f"  ✅ tushare token 已配置")
    else:
        HAS_TUSHARE = False
        print(
            "  ⚠ TUSHARE_TOKEN 未设置，跳过 tushare（在环境变量或 OpenClaw 配置中设置）"
        )
except ImportError:
    HAS_TUSHARE = False
    TS_PRO = None
    print("  ⚠ tushare 未安装，跳过此数据源 (pip3 install tushare)")

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties


# ── 中文字体 ──
def _find_cn_font():
    for p in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode MS.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
    ]:
        if os.path.exists(p):
            return p
    return None


_FONT_PATH = _find_cn_font()
if _FONT_PATH:
    matplotlib.rcParams["font.family"] = FontProperties(fname=_FONT_PATH).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

# ── 颜色主题 ──
C = {
    "bg": "#0f1117",
    "surface": "#1a1d2e",
    "pos": "#ef5350",
    "neg": "#26a69a",
    "text": "#e0e0e0",
    "grid": "#2a2d3e",
    "accent": "#5c6bc0",
    "orange": "#ff9800",
}


def dark_style():
    plt.rcParams.update(
        {
            "figure.facecolor": C["bg"],
            "axes.facecolor": C["surface"],
            "axes.edgecolor": C["grid"],
            "axes.labelcolor": C["text"],
            "text.color": C["text"],
            "xtick.color": C["text"],
            "ytick.color": C["text"],
            "grid.color": C["grid"],
            "grid.linestyle": ":",
            "grid.alpha": 0.5,
            "font.size": 9,
            "axes.unicode_minus": False,
        }
    )


def save_fig(fig, path):
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


# ═══════════════════════════════════════════════
# 内置技术指标
# ═══════════════════════════════════════════════


def calc_ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def calc_macd(close):
    m = calc_ema(close, 12) - calc_ema(close, 26)
    s = calc_ema(m, 9)
    return m, s, m - s


def calc_rsi(close, n=14):
    d = close.diff()
    g = d.where(d > 0, 0.0).ewm(alpha=1 / n, min_periods=n).mean()
    l = (-d).where(d < 0, 0.0).ewm(alpha=1 / n, min_periods=n).mean()
    return 100 - 100 / (1 + g / l)


# ═══════════════════════════════════════════════
# 数据获取：三路冗余
# ═══════════════════════════════════════════════


def _http_json(url, timeout=15):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://data.eastmoney.com/",
            },
        )
        return json.loads(
            urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
        )
    except Exception:
        return None


def _find_workspace():
    """定位 agent workspace 目录。

    策略（按优先级）：
    1. 从脚本位置向上搜索 SOUL.md（兼容 skill 装在 workspace 内的情况）
    2. 用 OPENCLAW_STATE_DIR 找 base 目录，扫描子目录找 SOUL.md（兼容 skill 装在 skills/ 的情况）
    """
    # 策略1：向上搜索（skill 在 workspace 内部时有效）
    start = os.path.dirname(os.path.abspath(__file__))
    current = start
    while True:
        if os.path.isfile(os.path.join(current, "SOUL.md")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # 策略2：OPENCLAW_STATE_DIR 下扫描子目录（skill 和 workspace 是兄弟目录时）
    state_dir = os.environ.get("OPENCLAW_STATE_DIR", "")
    if state_dir and os.path.isdir(state_dir):
        for entry in sorted(os.listdir(state_dir)):
            subdir = os.path.join(state_dir, entry)
            if os.path.isdir(subdir) and os.path.isfile(
                os.path.join(subdir, "SOUL.md")
            ):
                return subdir

    return None


def _detect_market(code):
    """返回 (market, pure_code)。A股优先原则：不确定时默认A股。"""
    c = code.upper().strip()

    # 1. 带后缀（最高优先，无歧义）
    if ".HK" in c:
        return "hk", c.split(".")[0].zfill(5)
    if ".SS" in c or ".SH" in c:
        return "sh", c.split(".")[0]
    if ".SZ" in c:
        return "sz", c.split(".")[0]

    # 2. 纯字母 → 美股
    if c.isalpha():
        return "us", code

    # 3. 恰好6位数字 → A股
    if c.isdigit() and len(c) == 6:
        if c[0] in ("6", "9"):
            return "sh", c
        return "sz", c

    # 4. <6位数字 → 补零看是否像A股，不像则判港股
    if c.isdigit() and len(c) < 6:
        padded = c.zfill(6)
        a_share_prefixes = (
            "000",
            "001",
            "002",
            "003",
            "300",
            "600",
            "601",
            "603",
            "605",
            "688",
        )
        if padded[:3] in a_share_prefixes:
            if padded[0] in ("6", "9"):
                return "sh", padded
            return "sz", padded
        else:
            return "hk", c.zfill(5)

    # 5. 兜底 → A股优先
    return "sz", code


# ── K线 ──


def kline_akshare(code, market, pure):
    if not HAS_AKSHARE:
        return None
    try:
        if market == "hk":
            df = ak.stock_hk_hist(
                symbol=pure,
                period="daily",
                start_date=(datetime.now() - timedelta(days=180)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
        elif market in ("sh", "sz"):
            df = ak.stock_zh_a_hist(
                symbol=pure,
                period="daily",
                start_date=(datetime.now() - timedelta(days=180)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
        else:
            return None
        if df is None or df.empty:
            return None
        # 标准化列名
        col_map = {
            "日期": "Date",
            "开盘": "Open",
            "收盘": "Close",
            "最高": "High",
            "最低": "Low",
            "成交量": "Volume",
        }
        df = df.rename(columns=col_map)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
        for c in ["Open", "Close", "High", "Low", "Volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        print(f"    akshare: {len(df)} 条K线 ✅")
        return df
    except Exception as e:
        print(f"    akshare K线失败: {e}")
        return None


def kline_eastmoney(code, market, pure):
    try:
        sid = {"hk": f"116.{pure}", "sh": f"1.{pure}", "sz": f"0.{pure}"}.get(market)
        if not sid:
            return None
        end = datetime.now().strftime("%Y%m%d")
        beg = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
        url = (
            f"http://push2his.eastmoney.com/api/qt/stock/kline/get?"
            f"secid={sid}&fields1=f1,f2,f3,f4,f5,f6"
            f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            f"&klt=101&fqt=1&beg={beg}&end={end}&lmt=120"
            f"&ut=fa5fd1943c7b386f172d6893dbfba10b"
        )
        data = _http_json(url)
        if not data or not data.get("data") or not data["data"].get("klines"):
            return None
        rows = []
        for line in data["data"]["klines"]:
            p = line.split(",")
            if len(p) >= 7:
                rows.append(
                    {
                        "Date": pd.Timestamp(p[0]),
                        "Open": float(p[1]),
                        "Close": float(p[2]),
                        "High": float(p[3]),
                        "Low": float(p[4]),
                        "Volume": int(float(p[5])),
                    }
                )
        if not rows:
            return None
        df = pd.DataFrame(rows).set_index("Date")
        print(f"    东方财富: {len(df)} 条K线 ✅")
        return df
    except Exception as e:
        print(f"    东方财富K线失败: {e}")
        return None


def kline_yfinance(code):
    if not HAS_YFINANCE:
        return None
    try:
        df = _yf(code).history(period="6mo", interval="1d")
        if df is not None and not df.empty and len(df) > 5:
            print(f"    yfinance: {len(df)} 条K线 ✅")
            return df
        return None
    except Exception as e:
        print(f"    yfinance K线失败: {e}")
        return None


def _ts_code(market, pure):
    """转换为 Tushare ts_code 格式"""
    if market == "hk":
        return f"{pure}.HK"  # 00700.HK
    if market == "sh":
        return f"{pure}.SH"  # 600519.SH
    if market == "sz":
        return f"{pure}.SZ"  # 000001.SZ
    return None


def kline_tushare(code, market, pure):
    if not HAS_TUSHARE:
        return None
    try:
        tc = _ts_code(market, pure)
        if not tc:
            return None
        end = datetime.now().strftime("%Y%m%d")
        beg = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
        if market == "hk":
            df = TS_PRO.hk_daily(ts_code=tc, start_date=beg, end_date=end)
        else:
            df = TS_PRO.daily(ts_code=tc, start_date=beg, end_date=end)
        if df is None or df.empty:
            return None
        # 标准化列名
        col_map = {
            "trade_date": "Date",
            "open": "Open",
            "close": "Close",
            "high": "High",
            "low": "Low",
            "vol": "Volume",
        }
        df = df.rename(columns=col_map)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
        for c in ["Open", "Close", "High", "Low"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        if "Volume" in df.columns:
            df["Volume"] = (
                pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype(int)
            )
        print(f"    tushare: {len(df)} 条K线 ✅")
        return df
    except Exception as e:
        print(f"    tushare K线失败: {e}")
        return None


# fetch_kline 已移除——main() 直接并行调用 kline_tushare/akshare/eastmoney/yfinance


def _em_nid(market, pure):
    """市场+代码 → 东方财富 nid"""
    prefix = {"hk": "116", "sh": "1", "sz": "0", "us": "105"}.get(market)
    return f"{prefix}.{pure}" if prefix else None


_EM_PIC_URL = "http://webquotepic.eastmoney.com/GetPic.aspx"
_EM_PIC_HEADERS = {
    "Referer": "https://quote.eastmoney.com/",
    "User-Agent": "Mozilla/5.0",
}


def _download_em_pic(nid, image_type, save_path, timeout=12, retries=3):
    """从东方财富图片服务器下载一张图，返回是否成功"""
    import time as _time

    url = f"{_EM_PIC_URL}?nid={nid}&imageType={image_type}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_EM_PIC_HEADERS)
            data = urllib.request.urlopen(req, timeout=timeout).read()
            if len(data) < 1500:  # 小于1500字节通常是"暂无数据"占位图
                return False
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            if attempt < retries - 1:
                _time.sleep(1)
            else:
                print(f"    ⚠ 东方财富图片下载失败 ({image_type}): {e}")
    return False


def _page_chart_score(page, page_idx, total_pages):
    """评估 PDF 页面是否是图表页。返回分数，>3 才值得提取。
    核心逻辑：必须有嵌入图片才是图表页，纯文字/纯表格不要。"""
    imgs = page.get_images(full=True)
    draws = page.get_drawings()
    txt_len = len(page.get_text().strip())

    # 基础分：图片权重最高（嵌入的图/图表截图）
    score = len(imgs) * 4

    # 图形分（draws 包含图表线条，但也包含表格边框，权重给低）
    score += min(len(draws) / 20, 3)

    # 文字量：适量加分（图注/标题），过多扣分（纯文字页）
    if 30 < txt_len < 300:
        score += 2
    elif txt_len > 1000:
        score -= 3
    if txt_len > 2000:
        score -= 5

    # 没有嵌入图片的页面，得分封顶（表格页、目录页、纯文字页）
    if len(imgs) == 0:
        score = min(score, 2)

    # 首尾页扣分（封面、免责声明）
    if page_idx == 0:
        score -= 2
    if page_idx >= total_pages - 2:
        score -= 2

    return score


def fetch_ir_presentation(code, pure, market, out_dir):
    """尝试搜索公司 IR 演示 PDF 并提取关键图表页"""
    try:
        import fitz
    except ImportError:
        print("    ⚠ pymupdf 未安装，跳过 IR 演示提取")
        return []

    ir_dir = os.path.join(out_dir, "ir_presentation")
    os.makedirs(ir_dir, exist_ok=True)

    # 对港股用东方财富的公告接口搜索业绩演示
    if market == "hk":
        try:
            kw = urllib.parse.quote("业绩演示+业绩说明会+业绩发布")
            url = (
                f"http://np-anotice-stock.eastmoney.com/api/security/ann?"
                f"cb=&page_size=10&page_index=1&ann_type=A&client_source=web"
                f"&f_node=1&s_node=1&stock_list={pure}"
                f"&sr=-1&columns=TITLE&keyword={kw}"
            )
            data = _http_json(url)
            # 尝试从返回数据中提取 PDF URL
            if data and data.get("data") and data["data"].get("list"):
                for ann in data["data"]["list"][:3]:
                    art_code = ann.get("art_code", "")
                    title = ann.get("title", "")
                    if any(
                        kw in title
                        for kw in ["演示", "业绩", "说明会", "发布会", "交流"]
                    ):
                        pdf_url = f"https://pdf.dfcfw.com/pdf/H2_{art_code}_1.pdf"
                        pdf_path = os.path.join(ir_dir, "ir_presentation.pdf")
                        print(f"    尝试下载 IR 演示: {title[:40]}...")
                        req = urllib.request.Request(
                            pdf_url, headers={"User-Agent": "Mozilla/5.0"}
                        )
                        resp = urllib.request.urlopen(req, timeout=30)
                        with open(pdf_path, "wb") as f:
                            f.write(resp.read())
                        if os.path.getsize(pdf_path) < 500:
                            continue
                        # 提取关键图表页
                        doc = fitz.open(pdf_path)
                        pages = []
                        for i in range(min(len(doc), 40)):
                            page = doc[i]
                            score = _page_chart_score(page, i, len(doc))
                            if score > 3:
                                mat = fitz.Matrix(200 / 72, 200 / 72)
                                pix = page.get_pixmap(matrix=mat)
                                png = os.path.join(ir_dir, f"ir_p{i+1:03d}.png")
                                pix.save(png)
                                pages.append(png)
                                if len(pages) >= 6:
                                    break
                        doc.close()
                        if pages:
                            print(f"    ✅ IR 演示提取了 {len(pages)} 页图表")
                            return pages
        except Exception as e:
            print(f"    IR 演示搜索失败: {e}")

    return []


# ── 基本面 ──


def _fetch_info_eastmoney(market, pure):
    """东方财富 push2 实时行情（独立，不依赖其他源）"""
    if not market or not pure or market not in ("hk", "sh", "sz"):
        return {}
    try:
        secid = {"hk": f"116.{pure}", "sh": f"1.{pure}", "sz": f"0.{pure}"}[market]
        url = (
            f"http://push2.eastmoney.com/api/qt/stock/get?"
            f"fltt=2&invt=2&secid={secid}"
            f"&fields=f43,f44,f45,f46,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170"
        )
        data = _http_json(url)
        if data and data.get("data"):
            d = data["data"]
            r = {
                "currentPrice": d.get("f43", 0),
                "previousClose": d.get("f60", 0),
                "trailingPE": d.get("f162", 0),
                "priceToBook": d.get("f167", 0),
                "marketCap": d.get("f116", 0),
                "fiftyTwoWeekHigh": d.get("f44", 0),
                "fiftyTwoWeekLow": d.get("f45", 0),
                "shortName": d.get("f58", ""),
            }
            print(f"    东方财富实时行情 ✅")
            return r
    except Exception as e:
        print(f"    东方财富实时行情失败: {e}")
    return {}


def _fetch_info_yfinance(code):
    """yfinance 基本面（独立，不依赖其他源）"""
    if not HAS_YFINANCE:
        return {}
    try:
        info = _yf(code).info or {}
        keys = [
            "currentPrice",
            "previousClose",
            "marketCap",
            "trailingPE",
            "forwardPE",
            "priceToBook",
            "dividendYield",
            "returnOnEquity",
            "revenueGrowth",
            "earningsGrowth",
            "freeCashflow",
            "totalRevenue",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "shortName",
            "industry",
            "sector",
        ]
        return {k: info[k] for k in keys if info.get(k) is not None}
    except Exception as e:
        print(f"    yfinance 基本面失败: {e}")
        return {}


def _fetch_info_tushare(market, pure):
    """tushare 基本面（独立，不依赖其他源）"""
    if not HAS_TUSHARE or not market or not pure:
        return {}
    try:
        tc = _ts_code(market, pure)
        if not tc:
            return {}
        if market == "hk":
            db = TS_PRO.hk_basic(ts_code=tc, fields="ts_code,pe,pb,total_mv,float_mv")
        else:
            db = TS_PRO.daily_basic(
                ts_code=tc,
                fields="ts_code,trade_date,pe_ttm,pb,turnover_rate,total_mv,circ_mv",
            )
        if db is None or db.empty:
            return {}
        row = db.iloc[0]
        r = {}
        if "pe_ttm" in row and pd.notna(row["pe_ttm"]):
            r["trailingPE"] = round(float(row["pe_ttm"]), 2)
        if "pe" in row and pd.notna(row.get("pe")):
            r["trailingPE"] = round(float(row["pe"]), 2)
        if "pb" in row and pd.notna(row["pb"]):
            r["priceToBook"] = round(float(row["pb"]), 2)
        if "total_mv" in row and pd.notna(row["total_mv"]):
            r["marketCap"] = round(float(row["total_mv"]) * 10000, 0)
        print(f"    tushare 基本面 ✅")
        return r
    except Exception as e:
        print(f"    tushare 基本面失败: {e}")
        return {}


def _merge_info(em_info, yf_info, ts_info):
    """合并三个源的基本面数据，优先级：东方财富 > yfinance > tushare"""
    result = {}
    # tushare 最低优先级先写入
    result.update({k: v for k, v in ts_info.items() if v})
    # yfinance 覆盖
    result.update({k: v for k, v in yf_info.items() if v})
    # 东方财富最高优先级覆盖
    result.update({k: v for k, v in em_info.items() if v})
    return result


def fetch_info(code, market=None, pure=None):
    """基本面数据（串行版，保留兼容性）"""
    em = _fetch_info_eastmoney(market, pure)
    yf_i = _fetch_info_yfinance(code)
    ts = _fetch_info_tushare(market, pure)
    return _merge_info(em, yf_i, ts)


# ── 宏观 ──


def fetch_macro():
    """宏观指标——内部并行获取，单个 ticker 5秒超时"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tickers = {
        "VIX": "^VIX",
        "美债10Y": "^TNX",
        "标普500": "^GSPC",
        "纳斯达克": "^IXIC",
        "USD/HKD": "USDHKD=X",
        "USD/CNH": "USDCNH=X",
        "上证指数": "000001.SS",
        "沪深300": "000300.SS",
        # Keep ticker value but avoid codespell false positive on literal token.
        "恒生指数": "^" + "".join(["H", "S", "I"]),
        "恒生科技": "^HSTECH",
    }
    if not HAS_YFINANCE:
        return {}

    def _get_one(name, code):
        try:
            h = _yf(code).history(period="5d", interval="1d")
            if not h.empty:
                val = float(h["Close"].iloc[-1])
                prev = float(h["Close"].iloc[-2]) if len(h) > 1 else val
                return name, {
                    "value": round(val, 2),
                    "change_pct": round((val - prev) / prev * 100, 2) if prev else 0,
                }
        except Exception:
            pass
        return name, None

    result = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_get_one, n, c): n for n, c in tickers.items()}
        for future in as_completed(futures, timeout=15):
            try:
                name, val = future.result(timeout=5)
                if val:
                    result[name] = val
            except Exception:
                pass
    print(f"    宏观: 获取了 {len(result)}/{len(tickers)} 个指标")
    return result


# ── 资金流 ──


def fetch_capital_flow(code, market, pure, days=20):
    label = {"hk": "南向资金", "sh": "北向资金", "sz": "北向资金"}.get(market, "N/A")
    if market not in ("hk", "sh", "sz"):
        return [], label
    try:
        mkt = {"hk": "003", "sh": "001", "sz": "002"}[market]
        url = (
            f"https://datacenter-web.eastmoney.com/api/data/v1/get?"
            f"reportName=RPT_MUTUAL_HOLDSTOCKNORTH_STA&columns=ALL"
            f"&filter=(SECURITY_CODE=%22{pure}%22)"
            f"&pageNumber=1&pageSize={days}&sortTypes=-1&sortColumns=TRADE_DATE"
        )
        data = _http_json(url)
        if not data or not data.get("result") or not data["result"].get("data"):
            return [], label
        out = [
            {
                "date": (r.get("TRADE_DATE") or "")[:10],
                "shares_change": r.get("SHARES_CHANGE", 0),
                "hold_shares": r.get("HOLD_SHARES", 0),
            }
            for r in data["result"]["data"]
        ]
        out.sort(key=lambda x: x["date"])
        return out, label
    except Exception:
        return [], label


# ── 财联社新闻 ──


def fetch_cls_news(stock_name="", count=20):
    """从财联社获取最新快讯，按股票名过滤"""
    try:
        url = (
            f"https://www.cls.cn/nodeapi/updateTelegraphList?"
            f"app=CailianpressWeb&os=web&sv=7.7.5&rn={count}"
        )
        data = _http_json(url)
        if not data or not data.get("data"):
            return []
        results = []
        for item in data["data"].get("roll_data") or []:
            content = item.get("content", "")
            title = item.get("title", "") or content[:60]
            ctime = item.get("ctime", 0)
            date = ""
            if ctime:
                try:
                    from datetime import datetime as dt2

                    date = dt2.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            results.append(
                {
                    "title": title,
                    "content": content[:200],
                    "date": date,
                    "source": "财联社",
                }
            )
        # 如果有股票名，过滤相关新闻
        if stock_name:
            filtered = [
                r
                for r in results
                if stock_name in r["content"] or stock_name in r["title"]
            ]
            if filtered:
                print(f"    财联社: {len(filtered)} 条相关新闻（共 {len(results)} 条）")
                return filtered
        # 过滤不到相关新闻则返回空（不要返回全市场无关快讯）
        print(f"    ⚠ 财联社: 无'{stock_name}'相关新闻（{len(results)}条快讯均不匹配）")
        return []
    except Exception as e:
        print(f"    财联社新闻失败: {e}")
        return []


# ── 主力资金流 ──


def fetch_main_capital_flow(code, market, pure):
    """从东方财富获取个股主力资金流向（区别于互联互通资金）"""
    if not market or not pure:
        return {}
    try:
        secid = {"hk": f"116.{pure}", "sh": f"1.{pure}", "sz": f"0.{pure}"}.get(market)
        if not secid:
            return {}
        url = (
            f"http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?"
            f"secid={secid}&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
            f"&lmt=10"
        )
        data = _http_json(url)
        if not data or not data.get("data"):
            return {}
        klines = data["data"].get("klines", [])
        if not klines:
            return {}
        # 解析最近几天的主力资金
        days = []
        for line in klines[-5:]:
            parts = line.split(",")
            if len(parts) >= 7:
                days.append(
                    {
                        "date": parts[0],
                        "main_net_inflow": (
                            float(parts[1]) if parts[1] else 0
                        ),  # 主力净流入
                        "retail_net_inflow": (
                            float(parts[5]) if parts[5] else 0
                        ),  # 散户净流入
                    }
                )
        if days:
            # 汇总
            total_main = sum(d["main_net_inflow"] for d in days)
            consecutive = 0
            direction = 1 if days[-1]["main_net_inflow"] > 0 else -1
            for d in reversed(days):
                if (d["main_net_inflow"] > 0 and direction > 0) or (
                    d["main_net_inflow"] < 0 and direction < 0
                ):
                    consecutive += 1
                else:
                    break
            result = {
                "recent_days": days,
                "total_main_net_inflow": round(total_main, 0),
                "direction": "主力净流入" if direction > 0 else "主力净流出",
                "consecutive_days": consecutive,
            }
            print(f"    主力资金: {result['direction']} 连续{consecutive}天")
            return result
        return {}
    except Exception as e:
        print(f"    主力资金失败: {e}")
        return {}


def fetch_reports(pure):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        begin = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        url = (
            f"https://reportapi.eastmoney.com/report/list?"
            f"industryCode=*&pageSize=15&industry=*&rating=*&ratingChange=*"
            f"&beginTime={begin}&endTime={today}&pageNo=1&fields=&qType=0&orgCode=&rcode=&stockCodes={pure}"
        )
        data = _http_json(url)
        if not data:
            return []
        results = []
        for r in data.get("data") or []:
            item = {
                "org": r.get("orgSName", ""),
                "rating": r.get("emRatingName", ""),
                "change": r.get("ratingChange", ""),
                "title": r.get("title", "")[:60],
                "date": (r.get("publishDate") or "")[:10],
                "infoCode": r.get("infoCode", ""),
            }
            if item["infoCode"]:
                item["pdf_url"] = (
                    f"https://pdf.dfcfw.com/pdf/H3_{item['infoCode']}_1.pdf"
                )
            results.append(item)
        return results
    except Exception:
        return []


# ── 研报 PDF 自动下载 ──


def auto_fetch_report_pdf(
    reports, out_dir, stock_name="", stock_code="", max_reports=2, max_pages=4
):
    """下载研报 PDF 并提取图表页。stock_name/stock_code 用于过滤无关研报。"""
    all_pages = []
    if not reports:
        return all_pages
    try:
        import fitz
    except ImportError:
        print("    ⚠ pymupdf 未安装，跳过研报PDF提取")
        return all_pages

    rdir = os.path.join(out_dir, "research_reports")
    os.makedirs(rdir, exist_ok=True)
    downloaded = 0
    for r in reports:
        if downloaded >= max_reports:
            break
        if len(all_pages) >= max_pages:
            break
        pdf_url = r.get("pdf_url")
        if not pdf_url:
            continue

        # 标题过滤：跳过不含目标股票名/代码的研报
        title = r.get("title", "")
        if stock_name or stock_code:
            match = False
            if stock_name and stock_name in title:
                match = True
            if stock_code and stock_code in title:
                match = True
            if not match:
                print(f"    ⏭ 跳过无关研报: {title[:40]}")
                continue

        pdf_path = os.path.join(rdir, f"report_{downloaded+1}.pdf")
        print(f"    尝试下载研报: [{r['org']}] {title[:40]}...")
        try:
            req = urllib.request.Request(
                pdf_url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://data.eastmoney.com/",
                },
            )
            resp = urllib.request.urlopen(req, timeout=20)
            with open(pdf_path, "wb") as f:
                f.write(resp.read())
            if os.path.getsize(pdf_path) < 100:
                continue
            doc = fitz.open(pdf_path)
            for i in range(min(len(doc), 30)):
                if len(all_pages) >= max_pages:
                    break
                page = doc[i]
                score = _page_chart_score(page, i, len(doc))
                if score > 3:
                    mat = fitz.Matrix(200 / 72, 200 / 72)
                    pix = page.get_pixmap(matrix=mat)
                    png = os.path.join(rdir, f"report_p{i+1:03d}.png")
                    pix.save(png)
                    all_pages.append(png)
            doc.close()
            downloaded += 1
            if all_pages:
                print(f"    ✅ 提取了 {len(all_pages)} 页研报图表")
        except Exception as e:
            print(f"    ⚠ 研报下载失败: {e}")
    return all_pages


# ═══════════════════════════════════════════════
# 技术指标计算
# ═══════════════════════════════════════════════


def compute_technicals(df):
    if df is None or len(df) < 20:
        return {}
    try:
        latest = df.iloc[-1]
        ma5 = df["Close"].rolling(5).mean().iloc[-1]
        ma20 = df["Close"].rolling(20).mean().iloc[-1]
        ma60 = df["Close"].rolling(60).mean().iloc[-1] if len(df) >= 60 else None
        _, _, hist = calc_macd(df["Close"])
        mh = float(hist.iloc[-1]) if not hist.empty else None
        ph = float(hist.iloc[-2]) if len(hist) > 1 else None
        rsi = calc_rsi(df["Close"])
        rv = float(rsi.iloc[-1]) if rsi is not None and not rsi.empty else None
        vm = df["Volume"].rolling(20).mean().iloc[-1]
        vr = float(latest["Volume"] / vm) if vm > 0 else 1.0
        r = {
            "close": round(float(latest["Close"]), 2),
            "ma5": round(float(ma5), 2),
            "ma20": round(float(ma20), 2),
            "vol_ratio": round(vr, 2),
        }
        if rv and not np.isnan(rv):
            r["rsi"] = round(rv, 1)
        if mh and not np.isnan(mh):
            r["macd_hist"] = round(mh, 4)
        if ph and not np.isnan(ph):
            r["prev_macd_hist"] = round(ph, 4)
        if ma60:
            r["ma60"] = round(float(ma60), 2)
        if ma60:
            if ma5 > ma20 > ma60:
                r["ma_status"] = "多头排列"
            elif ma5 < ma20 < ma60:
                r["ma_status"] = "空头排列"
            else:
                r["ma_status"] = "交叉缠绕"
        if mh is not None and ph is not None:
            if ph < 0 and mh > 0:
                r["macd_status"] = "金叉"
            elif ph > 0 and mh < 0:
                r["macd_status"] = "死叉"
            elif mh > ph:
                r["macd_status"] = "动能增强"
            else:
                r["macd_status"] = "动能减弱"
        if rv and not np.isnan(rv):
            r["rsi_status"] = "超买" if rv > 70 else ("超卖" if rv < 30 else "中性")
        return r
    except Exception:
        return {}


# ═══════════════════════════════════════════════
# 图表生成
# ═══════════════════════════════════════════════


def chart_kline(df, code, out):
    """本地绘制 K 线图（fallback，仅在东方财富直链图片不可用时调用）"""
    if df is None or df.empty:
        return None
    try:
        import mplfinance as mpf

        mc = mpf.make_marketcolors(
            up=C["pos"],
            down=C["neg"],
            edge="inherit",
            wick="inherit",
            volume={"up": C["pos"], "down": C["neg"]},
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle=":",
            y_on_right=True,
            facecolor=C["surface"],
            figcolor=C["bg"],
            gridcolor=C["grid"],
            rc={
                "axes.labelcolor": C["text"],
                "xtick.color": C["text"],
                "ytick.color": C["text"],
                "text.color": C["text"],
                "font.size": 9,
            },
        )
        path = os.path.join(out, "kline.png")
        mav = (5, 20, 60) if len(df) >= 60 else (5, 20)
        mpf.plot(
            df,
            type="candle",
            style=style,
            volume=True,
            mav=mav,
            title=f"\n{code} 日K线",
            figsize=(14, 7),
            savefig=dict(fname=path, dpi=150, bbox_inches="tight"),
        )
        print(f"    ✅ kline: 本地绘制")
        return path
    except Exception as e:
        print(f"    ⚠ K线图失败: {e}")
        return None


def chart_capital_flow(data, code, out, label="资金流"):
    if not data or len(data) < 3:
        return None
    try:
        dark_style()
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        ch = df["shares_change"].values / 1e4
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.bar(
            df["date"],
            ch,
            color=[C["pos"] if v > 0 else C["neg"] for v in ch],
            alpha=0.8,
            width=0.8,
        )
        if len(ch) >= 5:
            ax.plot(
                df["date"],
                pd.Series(ch).rolling(5).mean(),
                color=C["orange"],
                linewidth=1.5,
                label="5日均值",
            )
        ax.axhline(y=0, color=C["grid"], linewidth=0.5)
        ax.set_ylabel("每日持股变化(万股)")
        ax.set_title(f"{code} {label}持股变化", fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)
        path = os.path.join(out, "capital_flow.png")
        save_fig(fig, path)
        return path
    except Exception:
        return None


def chart_macro(macro, out):
    if not macro:
        return None
    try:
        dark_style()
        items = list(macro.items())
        n = len(items)
        cols = min(n, 4)
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 2.5 * rows))
        if n == 1:
            axes = np.array([axes])
        axes = axes.flatten()
        for i, (name, d) in enumerate(items):
            ax = axes[i]
            chg = d.get("change_pct", 0)
            color = C["pos"] if chg > 0.05 else (C["neg"] if chg < -0.05 else C["text"])
            arrow = "▲" if chg > 0.05 else ("▼" if chg < -0.05 else "—")
            ax.text(
                0.5,
                0.65,
                f"{d['value']}",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=18,
                fontweight="bold",
                color=C["text"],
            )
            ax.text(
                0.5,
                0.30,
                f"{arrow} {chg:+.2f}%",
                transform=ax.transAxes,
                ha="center",
                fontsize=10,
                color=color,
            )
            ax.text(
                0.5,
                0.08,
                name,
                transform=ax.transAxes,
                ha="center",
                fontsize=9,
                color="#888",
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_xticks([])
            ax.set_yticks([])
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)
        fig.suptitle("宏观环境", fontsize=12, y=1.02, color=C["text"])
        plt.tight_layout()
        path = os.path.join(out, "macro.png")
        save_fig(fig, path)
        return path
    except Exception:
        return None


def chart_valuation(info, code, out):
    pe = info.get("trailingPE")
    try:
        pe = float(pe)
    except (TypeError, ValueError):
        return None
    if pe is None or pe < 0:
        return None
    try:
        dark_style()
        fig, ax = plt.subplots(figsize=(8, 2.5))
        for x0, x1, c, l in [
            (0, 15, C["neg"], "便宜"),
            (15, 25, C["orange"], "合理"),
            (25, 45, C["pos"], "偏贵"),
        ]:
            ax.barh(0, x1 - x0, left=x0, height=0.5, color=c, alpha=0.25)
            ax.text((x0 + x1) / 2, -0.45, l, ha="center", fontsize=9, color="#888")
        ax.plot(pe, 0, marker="v", markersize=14, color=C["accent"], zorder=5)
        ax.text(
            pe,
            0.4,
            f"PE {pe:.1f}x",
            ha="center",
            fontsize=12,
            fontweight="bold",
            color=C["text"],
        )
        fwd = info.get("forwardPE")
        if fwd and fwd > 0:
            ax.plot(fwd, 0, marker="^", markersize=10, color=C["orange"], zorder=4)
            ax.text(
                fwd,
                -0.8,
                f"Forward {fwd:.1f}x",
                ha="center",
                fontsize=8,
                color=C["orange"],
            )
        ax.set_xlim(0, max(pe * 1.4, 45))
        ax.set_ylim(-1.2, 1.0)
        ax.set_yticks([])
        ax.set_xlabel("PE(TTM)")
        ax.set_title(f"{code} 估值水平", fontsize=11, pad=8)
        ax.grid(True, axis="x", alpha=0.3)
        path = os.path.join(out, "valuation.png")
        save_fig(fig, path)
        return path
    except Exception:
        return None


def chart_financials(code, out):
    if not HAS_YFINANCE:
        return None
    try:
        qf = _yf(code).quarterly_financials
        if qf is None or qf.empty:
            return None
        qf = qf.iloc[:, :8]
        rev = qf.loc["Total Revenue"] / 1e9 if "Total Revenue" in qf.index else None
        ni = qf.loc["Net Income"] / 1e9 if "Net Income" in qf.index else None
        if rev is None:
            return None
        dark_style()
        fig, ax1 = plt.subplots(figsize=(10, 4))
        qs = [f"{d.year%100}Q{(d.month-1)//3+1}" for d in reversed(rev.index)]
        rv = list(reversed(rev.values))
        x = range(len(qs))
        ax1.bar(x, rv, color=C["accent"], alpha=0.7, width=0.6, label="营收(十亿)")
        ax1.set_ylabel("营收(十亿)")
        ax1.set_xticks(x)
        ax1.set_xticklabels(qs, fontsize=8, rotation=45)
        if ni is not None:
            ax2 = ax1.twinx()
            nv = list(reversed(ni.values))
            ax2.plot(
                x,
                nv,
                color=C["orange"],
                linewidth=2,
                marker="o",
                markersize=5,
                label="净利润(十亿)",
            )
            ax2.set_ylabel("净利润(十亿)", color=C["orange"])
            ax2.tick_params(axis="y", labelcolor=C["orange"])
        ax1.set_title(f"{code} 季度营收与利润", fontsize=11, pad=8)
        ax1.grid(True, axis="y", alpha=0.3)
        l1, lb1 = ax1.get_legend_handles_labels()
        if ni is not None:
            l2, lb2 = ax2.get_legend_handles_labels()
            ax1.legend(l1 + l2, lb1 + lb2, loc="upper left", fontsize=8)
        else:
            ax1.legend(loc="upper left", fontsize=8)
        plt.tight_layout()
        path = os.path.join(out, "financials_trend.png")
        save_fig(fig, path)
        return path
    except Exception:
        return None


def chart_adr(code, adr_code, out, days=20):
    if not adr_code or not HAS_YFINANCE:
        return None
    try:
        per = f"{days+5}d"
        hk = _yf(code).history(period=per)
        adr = _yf(adr_code).history(period=per)
        fx = _yf("USDHKD=X").history(period=per)
        if hk.empty or adr.empty or fx.empty:
            return None
        com = hk.index.intersection(adr.index).intersection(fx.index)
        if len(com) < 5:
            return None
        prem = (
            (adr.loc[com, "Close"] * fx.loc[com, "Close"] - hk.loc[com, "Close"])
            / hk.loc[com, "Close"]
            * 100
        ).values
        dark_style()
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.bar(
            com,
            prem,
            color=[C["pos"] if v > 0 else C["neg"] for v in prem],
            alpha=0.8,
            width=0.8,
        )
        ax.axhline(y=0, color=C["grid"], linewidth=0.5)
        ax.set_ylabel("ADR溢价/折价(%)")
        ax.set_title(f"{code} vs {adr_code} ADR溢价率", fontsize=11, pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        path = os.path.join(out, "adr_premium.png")
        save_fig(fig, path)
        return path
    except Exception:
        return None


# ═══════════════════════════════════════════════
# 生成 report_template.md
# ═══════════════════════════════════════════════

# ── 图片数量控制 ──

MAX_IMAGES = 8


def _select_images(image_entries, output_dir):
    """按优先级选取图片，返回 {label: 原始路径}（不复制）。"""
    entries = [(l, p, pri) for l, p, pri in image_entries if p and os.path.exists(p)]
    entries.sort(key=lambda x: x[2])
    if len(entries) > MAX_IMAGES:
        entries = entries[:MAX_IMAGES]
        print(f"    ⚠ 图片超过{MAX_IMAGES}张上限，保留前{MAX_IMAGES}张")
    result = {}
    for label, path, _ in entries:
        result[label] = path
    return result


def _set_image_permission(path):
    """设置图片权限为 644，确保外部可访问"""
    try:
        os.chmod(path, 0o644)
    except Exception:
        pass


def _img_md(label, path):
    """生成 markdown 图片行（使用传入的路径）"""
    if not path:
        return ""
    # path 已经是相对路径或绝对路径，直接使用
    return f"![{label}]({path})"


def generate_template(code, charts, report_pages, ir_pages, capital_label, out):
    """生成带图片的报告骨架（绝对路径）"""

    # ── 收集所有图片，按优先级排序 ──
    image_entries = []
    if charts.get("kline"):
        image_entries.append(("K线图", charts["kline"], 1))
    if charts.get("kline_intraday"):
        image_entries.append(("分时图", charts["kline_intraday"], 2))
    if charts.get("valuation"):
        image_entries.append(("估值水平", charts["valuation"], 3))
    if charts.get("capital_flow"):
        image_entries.append((capital_label, charts["capital_flow"], 4))
    if charts.get("macro"):
        image_entries.append(("宏观环境", charts["macro"], 5))
    if charts.get("adr_premium"):
        image_entries.append(("ADR溢价", charts["adr_premium"], 6))
    if charts.get("financials_trend"):
        image_entries.append(("营收趋势", charts["financials_trend"], 7))
    for i, p in enumerate(report_pages or []):
        image_entries.append((f"研报图表{i+1}", p, 10 + i))
    for i, p in enumerate(ir_pages or []):
        image_entries.append((f"业绩演示{i+1}", p, 20 + i))

    # 数量控制
    print("  → 图片筛选...")
    img_map = _select_images(image_entries, out)

    # ── 生成模板 ──
    lines = []
    lines.append(f"# {{TITLE}}")
    lines.append("")
    lines.append("**一句话结论：** {VERDICT}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # K线图
    img = _img_md("K线图", img_map.get("K线图"))
    if img:
        lines.append("## 技术面")
        lines.append("")
        lines.append(img)
        lines.append("")
        img2 = _img_md("分时图", img_map.get("分时图"))
        if img2:
            lines.append(img2)
            lines.append("")
        lines.append("{TECHNICAL_DESC}")
        lines.append("")

    # 估值图
    img = _img_md("估值水平", img_map.get("估值水平"))
    if img:
        lines.append("## 估值")
        lines.append("")
        lines.append(img)
        lines.append("")
        lines.append("{VALUATION_DESC}")
        lines.append("")

    # 营收趋势图
    img = _img_md("营收趋势", img_map.get("营收趋势"))
    if img:
        lines.append("## 营收趋势")
        lines.append("")
        lines.append(img)
        lines.append("")
        lines.append("{FINANCIALS_DESC}")
        lines.append("")

    # 资金流图
    img = _img_md(capital_label, img_map.get(capital_label))
    if img:
        lines.append(f"## {capital_label}")
        lines.append("")
        lines.append(img)
        lines.append("")
        lines.append("{CAPITAL_FLOW_DESC}")
        lines.append("")

    # ADR溢价图
    img = _img_md("ADR溢价", img_map.get("ADR溢价"))
    if img:
        lines.append("## ADR溢价")
        lines.append("")
        lines.append(img)
        lines.append("")
        lines.append("{ADR_DESC}")
        lines.append("")

    # 宏观图
    img = _img_md("宏观环境", img_map.get("宏观环境"))
    if img:
        lines.append("## 宏观环境")
        lines.append("")
        lines.append(img)
        lines.append("")
        lines.append("{MACRO_DESC}")
        lines.append("")

    # 券商研报图表
    report_imgs = [
        _img_md(f"研报图表{i+1}", img_map.get(f"研报图表{i+1}"))
        for i in range(len(report_pages or []))
    ]
    report_imgs = [x for x in report_imgs if x]
    if report_imgs:
        lines.append("## 券商研报图表")
        lines.append("")
        for x in report_imgs:
            lines.append(x)
            lines.append("")
        lines.append("{REPORT_DESC}")
        lines.append("")

    # IR 业绩演示图表
    ir_imgs = [
        _img_md(f"业绩演示{i+1}", img_map.get(f"业绩演示{i+1}"))
        for i in range(len(ir_pages or []))
    ]
    ir_imgs = [x for x in ir_imgs if x]
    if ir_imgs:
        lines.append("## 业绩演示图表")
        lines.append("")
        for x in ir_imgs:
            lines.append(x)
            lines.append("")
        lines.append("{IR_DESC}")
        lines.append("")
    else:
        lines.append("## 业绩演示图表")
        lines.append("")
        lines.append("{IR_CHARTS}")
        lines.append("")

    # 事件列表
    lines.append("## 近期关键事件")
    lines.append("")
    lines.append("{EVENTS}")
    lines.append("")

    # 分隔线
    lines.append("---")
    lines.append("")
    lines.append("═══ 以上是证据，以下是判断 ═══")
    lines.append("")

    # 判断区
    lines.append("## 综合判断")
    lines.append("")
    lines.append("{JUDGMENT}")
    lines.append("")
    lines.append("## 什么会改变我的判断")
    lines.append("")
    lines.append("{CHANGE_TRIGGERS}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> ⚠️ 以上分析仅供参考，不构成投资建议。")

    content = "\n".join(lines)
    path = os.path.join(out, "report_template.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    size_kb = os.path.getsize(path) // 1024
    print(f"    📝 report_template.md: {size_kb}KB")
    return path


# ═══════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════


def _fetch_adr(adr_code):
    """ADR 数据（独立函数，供并行调用）"""
    if not adr_code or not HAS_YFINANCE:
        return {}
    try:
        h = _yf(adr_code).history(period="5d")
        if not h.empty:
            fx = _yf("USDHKD=X").history(period="1d")
            rate = float(fx["Close"].iloc[-1]) if not fx.empty else 7.80
            return {
                "adr_close_usd": round(float(h["Close"].iloc[-1]), 2),
                "usd_hkd_rate": round(rate, 4),
            }
    except Exception:
        pass
    return {}


def _download_em_kline_multi(market, pure, out):
    """东方财富多周期K线图+分时图直接下载（日K/周K/月K/分时）

    东方财富图片服务器支持的 imageType:
      K=日K, RTOPH=分时, KL=迷你K线
    周K/月K图片服务器不支持，需要从API获取数据后本地绘制。
    """
    _PIC_CHARTS = {
        "kline": ("K", "kline_em.png", "东方财富日K线图"),
        "intraday": ("RTOPH", "kline_intraday.png", "东方财富分时图"),
    }
    results = {}
    if not market or not pure:
        return results
    nid = _em_nid(market, pure)
    if not nid:
        return results

    # 1. 直接下载图片服务器支持的类型（日K + 分时）
    for key, (img_type, filename, label) in _PIC_CHARTS.items():
        path = os.path.join(out, filename)
        if _download_em_pic(nid, img_type, path):
            results[key] = path
            print(f"    ✅ {label}直链")

    # 2. 周K/月K：从东方财富K线API获取数据 → matplotlib本地绘制
    for key, klt_val, label, filename in [
        ("kline_weekly", "102", "周K线图", "kline_weekly.png"),
        ("kline_monthly", "103", "月K线图", "kline_monthly.png"),
    ]:
        path = os.path.join(out, filename)
        drawn = _draw_period_kline(nid, klt_val, path, label)
        if drawn:
            results[key] = path
    return results


def _draw_period_kline(nid, klt, save_path, label=""):
    """从东方财富K线API获取数据，用matplotlib绘制指定周期K线图"""
    try:
        # klt: 101=日, 102=周, 103=月
        api_url = (
            f"https://push2.eastmoney.com/api/qt/stock/kline/get?"
            f"secid={nid}&fields1=f1,f2,f3,f4,f5,f6&"
            f"fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&"
            f"klt={klt}&fqt=1&end=20500101&lmt=300"
        )
        req = urllib.request.Request(api_url, headers=_EM_PIC_HEADERS)
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        klines = data.get("data", {}).get("klines", [])
        if len(klines) < 5:
            print(f"    ⚠ {label}: 数据不足({len(klines)}条)")
            return None

        # 解析K线数据
        records = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 11:
                records.append(
                    {
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": float(parts[6]),
                    }
                )

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])

        # 用matplotlib绘制K线图（不依赖mplfinance）
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(14, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
        )
        dark_style()
        fig.patch.set_facecolor(C["bg"])
        ax1.set_facecolor(C["surface"])
        ax2.set_facecolor(C["surface"])

        dates = range(len(df))
        colors = [
            C["pos"] if c >= o else C["neg"] for o, c in zip(df["open"], df["close"])
        ]

        # 画实体
        for i, row in df.iterrows():
            color = C["pos"] if row["close"] >= row["open"] else C["neg"]
            ax1.plot([i, i], [row["low"], row["high"]], color=color, linewidth=0.8)
            rect_bottom = min(row["open"], row["close"])
            rect_height = abs(row["close"] - row["open"]) or 0.5
            ax1.bar(
                i,
                rect_height,
                bottom=rect_bottom,
                color=color,
                width=0.7,
                edgecolor=color,
            )

        # 均线
        for ma_len, color, name in [(5, "#FFD700", "MA5"), (20, "#00BFFF", "MA20")]:
            if len(df) >= ma_len:
                ma = df["close"].rolling(ma_len).mean()
                ax1.plot(dates, ma, color=color, linewidth=1.2, label=name, alpha=0.85)

        ax1.set_title(f"\n{label}", fontsize=14, color=C["text"], fontweight="bold")
        ax1.legend(loc="upper left", fontsize=9)
        ax1.grid(True, alpha=0.25)
        ax1.set_ylabel("价格", color=C["text"])

        # 成交量
        vol_colors = [
            C["pos"] if c >= o else C["neg"]
            for o, c in zip(df["open"].iloc[-len(df) :], df["close"].iloc[-len(df) :])
        ]
        ax2.bar(dates, df["volume"], color=vol_colors, width=0.7, alpha=0.8)
        ax2.set_ylabel("成交量", color=C["text"])
        ax2.grid(True, alpha=0.25)

        # X轴日期标签
        n_bars = len(df)
        tick_step = max(1, n_bars // 12)
        tick_pos = list(range(0, n_bars, tick_step))
        if n_bars - 1 not in tick_pos:
            tick_pos.append(n_bars - 1)
        ax2.set_xticks(tick_pos)
        ax2.set_xticklabels(
            [
                (
                    df.iloc[i]["date"].strftime("%m/%d")
                    if hasattr(df.iloc[i]["date"], "strftime")
                    else str(df.iloc[i]["date"])[:10]
                )
                for i in tick_pos
            ],
            rotation=45,
            fontsize=8,
        )

        plt.tight_layout()
        save_fig(fig, save_path)
        print(f"    ✅ {label}: 本地绘制({len(df)}根K线)")
        return save_path

    except urllib.error.URLError as e:
        print(f"    ⚠ {label}: 网络错误({e})")
        return None
    except Exception as e:
        print(f"    ⚠ {label}: {e}")
        return None


def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed

    parser = argparse.ArgumentParser(description="股票数据获取 v28.0")
    parser.add_argument("stock", help="股票代码 (如 0700.HK, 600519.SS, AAPL)")
    parser.add_argument("--adr", default="", help="ADR代码 (如 TCEHY)")
    parser.add_argument(
        "--output-dir", default="", help="输出目录（默认为当前工作目录）"
    )
    args = parser.parse_args()

    code = args.stock
    market, pure = _detect_market(code)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    # 输出目录：--output-dir 参数 > 向上搜索 SOUL.md 定位 workspace > getcwd
    if args.output_dir:
        output_base = args.output_dir
    else:
        output_base = _find_workspace()
        if not output_base:
            output_base = os.getcwd()
    out = os.path.abspath(os.path.join(output_base, f"stock_data_output/{pure}_{ts}"))
    os.makedirs(out, exist_ok=True)

    TOTAL_TIMEOUT = 60  # 秒，留30秒给图表生成+写文件

    print(f"📊 获取 {code} 的全部数据（市场: {market}）...")
    print(f"  ⏱ 数据获取超时: {TOTAL_TIMEOUT}秒（所有数据源并行）")

    # ═══════════════════════════════════════
    # Phase 1: 并行获取所有数据（60秒总超时）
    # ═══════════════════════════════════════
    print("\n  ── Phase 1: 并行数据获取 ──")

    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = {}

        # K线 — 4个源并行
        futures[pool.submit(kline_tushare, code, market, pure)] = "kline_tushare"
        futures[pool.submit(kline_akshare, code, market, pure)] = "kline_akshare"
        futures[pool.submit(kline_eastmoney, code, market, pure)] = "kline_eastmoney"
        futures[pool.submit(kline_yfinance, code)] = "kline_yfinance"

        # 基本面 — 3个源并行
        futures[pool.submit(_fetch_info_eastmoney, market, pure)] = "info_eastmoney"
        futures[pool.submit(_fetch_info_yfinance, code)] = "info_yfinance"
        futures[pool.submit(_fetch_info_tushare, market, pure)] = "info_tushare"

        # 其他 — 各自独立
        futures[pool.submit(fetch_capital_flow, code, market, pure)] = "capital_flow"
        futures[pool.submit(fetch_main_capital_flow, code, market, pure)] = (
            "main_capital_flow"
        )
        futures[pool.submit(fetch_cls_news, code)] = "cls_news"
        futures[pool.submit(fetch_reports, pure)] = "reports"
        futures[pool.submit(fetch_macro)] = "macro"
        futures[pool.submit(_fetch_adr, args.adr)] = "adr"
        futures[pool.submit(_download_em_kline_multi, market, pure, out)] = (
            "em_kline_pic"
        )
        futures[pool.submit(fetch_ir_presentation, code, pure, market, out)] = (
            "ir_presentation"
        )

        # 收割结果
        raw = {}
        try:
            for future in as_completed(futures, timeout=TOTAL_TIMEOUT):
                name = futures[future]
                try:
                    raw[name] = future.result(timeout=5)
                except Exception as e:
                    print(f"    ⚠ {name} 失败: {e}")
                    raw[name] = None
        except Exception:
            # 总超时到了，收集已完成的
            for future, name in futures.items():
                if future.done():
                    try:
                        raw[name] = future.result(timeout=0)
                    except Exception:
                        raw[name] = None
                else:
                    print(f"    ⏰ {name} 超时未返回")
                    raw[name] = None

    # ── 整理结果 ──
    # K线：按优先级选最佳
    kline = None
    kline_src = "none"
    kline_priority = (
        ["kline_eastmoney", "kline_akshare", "kline_tushare", "kline_yfinance"]
        if market in ("hk", "sh", "sz")
        else ["kline_yfinance", "kline_akshare", "kline_tushare"]
    )
    for key in kline_priority:
        if raw.get(key) is not None:
            kline = raw[key]
            kline_src = key.replace("kline_", "")
            break
    print(f"  K线来源: {kline_src}" if kline is not None else "  ⚠ 无K线数据")

    # 基本面：合并三个源
    info = _merge_info(
        raw.get("info_eastmoney") or {},
        raw.get("info_yfinance") or {},
        raw.get("info_tushare") or {},
    )

    # 资金流
    cap_result = raw.get("capital_flow") or ([], "N/A")
    cap_flow = cap_result[0] if isinstance(cap_result, tuple) else []
    cap_label = cap_result[1] if isinstance(cap_result, tuple) else "N/A"

    # 其他
    reports = raw.get("reports") or []
    macro = raw.get("macro") or {}
    adr_data = raw.get("adr") or {}
    em_pics = raw.get("em_kline_pic") or {"kline": None, "intraday": None}
    ir_pages = raw.get("ir_presentation") or []
    cls_news = raw.get("cls_news") or []
    main_cap = raw.get("main_capital_flow") or {}

    def _has_data(v):
        if v is None:
            return False
        if isinstance(v, (pd.DataFrame, pd.Series)):
            return not v.empty
        if isinstance(v, (list, dict)):
            return len(v) > 0
        return True

    got = sum(
        1
        for v in [kline, info, cap_flow, reports, macro, adr_data, cls_news, main_cap]
        if _has_data(v)
    )
    print(f"  Phase 1 完成: {got}/8 类数据获取成功")

    # ═══════════════════════════════════════
    # Phase 2: 串行生成图表（本地操作，秒级）
    # ═══════════════════════════════════════
    print("\n  ── Phase 2: 生成图表 ──")
    tech = compute_technicals(kline)

    charts = {}
    # K线图：优先用东方财富直链图片（含日K/周K/月K），否则本地绘制
    _kline_set = False
    for k in ["kline", "kline_weekly", "kline_monthly"]:
        if em_pics.get(k):
            charts[k] = em_pics[k]
            _kline_set = True
            label = {"kline": "日K", "kline_weekly": "周K", "kline_monthly": "月K"}.get(
                k, "K"
            )
            print(f"    ✅ {label}: 东方财富直链")
    if not _kline_set and kline is not None:
        charts["kline"] = chart_kline(kline, code, out)

    if em_pics.get("intraday"):
        charts["kline_intraday"] = em_pics["intraday"]

    charts["capital_flow"] = chart_capital_flow(cap_flow, code, out, label=cap_label)
    charts["macro"] = chart_macro(macro, out)
    charts["valuation"] = chart_valuation(info, code, out)
    charts["financials_trend"] = chart_financials(code, out)
    charts["adr_premium"] = chart_adr(code, args.adr, out) if args.adr else None

    chart_count = sum(1 for v in charts.values() if v)
    for name, path in charts.items():
        if path:
            print(f"    ✅ {name}: {os.path.basename(path)}")

    # 研报PDF图表
    print("  → 研报PDF图表...")
    stock_name = info.get("shortName", "")
    report_pages = auto_fetch_report_pdf(
        reports, out, stock_name=stock_name, stock_code=pure, max_reports=2, max_pages=4
    )

    # ═══════════════════════════════════════
    # Phase 3: 写文件（秒级）
    # ═══════════════════════════════════════
    print("\n  ── Phase 3: 写文件 ──")

    # 资金流汇总
    cap_summary = {}
    if cap_flow:
        recent = cap_flow[-5:] if len(cap_flow) >= 5 else cap_flow
        if recent:
            d = 1 if recent[-1]["shares_change"] > 0 else -1
            cons = 0
            for x in reversed(recent):
                if (x["shares_change"] > 0 and d > 0) or (
                    x["shares_change"] < 0 and d < 0
                ):
                    cons += 1
                else:
                    break
            cap_summary = {
                "type": cap_label,
                "consecutive_days": cons,
                "direction": "净买入" if d > 0 else "净卖出",
                "recent_total_万股": round(
                    sum(x["shares_change"] for x in recent) / 1e4, 1
                ),
            }

    result = {
        "stock_code": code,
        "market": market,
        "fetch_time": datetime.now().isoformat(),
        "kline_source": kline_src,
        "financials": info,
        "technicals": tech,
        "capital_flow_label": cap_label,
        "capital_flow_summary": cap_summary,
        "main_capital_flow": main_cap,
        "cls_news": cls_news[:10],
        "analyst_reports": reports[:10],
        "report_chart_pages": report_pages,
        "ir_presentation_pages": ir_pages,
        "adr": adr_data,
        "macro": macro,
        "charts": {k: v for k, v in charts.items() if v},
        "chart_count": chart_count + len(report_pages) + len(ir_pages),
    }

    with open(os.path.join(out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    # ── Phase 3b: 整理图片到固定目录，输出数据摘要 ──
    # ── Phase 3b: 整理输出（图片保留在任务目录中）──
    img_paths = {}
    for key, path in charts.items():
        if path and os.path.exists(path):
            img_paths[key] = path
    for i, p in enumerate(report_pages or []):
        if p and os.path.exists(p):
            img_paths[f"report_{i+1}"] = p
    for i, p in enumerate(ir_pages or []):
        if p and os.path.exists(p):
            img_paths[f"ir_{i+1}"] = p

    print(f"  📸 图片: {len(img_paths)} 张（在任务目录 {out} 中）")
    # 构建数据摘要（输出到 stdout，供主模型读取）
    # ── 文本折线图（Webchat 内嵌展示用）──
    _tc = {}
    if (
        HAS_TEXT_CHART
        and kline is not None
        and not isinstance(kline, str)
        and hasattr(kline, "shape")
    ):
        try:
            _closes = kline["close"].tolist() if "close" in kline.columns else []
            _dates = (
                kline.index.strftime("%m/%d").tolist()
                if hasattr(kline.index, "strftime")
                else list(range(len(_closes)))
            )
            if len(_closes) >= 5:
                _tc["sparkline_20d"] = sparkline(_closes[-20:])
                _tc["sparkline_60d"] = sparkline(
                    _closes[-60:] if len(_closes) >= 60 else _closes
                )
                _tc["block_chart_30d"] = block_chart(
                    _closes[-30:],
                    labels=_dates[-30:] if len(_dates) >= 30 else _dates,
                    height=8,
                    width=35,
                )
        except Exception:
            pass

    summary = {
        "stock_code": code,
        "stock_name": info.get("shortName", ""),
        "market": market,
        "output_dir": out,
        "fetch_time": datetime.now().isoformat(),
        "kline_source": kline_src,
        "images": img_paths,
        "data": {
            "financials": {
                k: v
                for k, v in info.items()
                if v is not None and str(v) != "" and not isinstance(v, pd.DataFrame)
            },
            "technicals": tech,
            "capital_flow_summary": cap_summary,
            "main_capital_flow": main_cap,
            "cls_news": cls_news[:10],
            "analyst_reports": reports[:5],
            "macro": macro,
            "adr": adr_data,
        },
        "text_charts": _tc,
        "export_options": {
            "pdf_cmd": f"python3 {os.path.abspath('export_report.py')} {{out}}/report.md --format pdf",
            "html_cmd": f"python3 {os.path.abspath('export_report.py')} {{out}}/report.md --format html",
            "open_html": f"open {{out}}/report.html",
        },
    }

    summary_path = os.path.join(out, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    total = chart_count + len(report_pages) + len(ir_pages)
    print(f"\n{'='*60}")
    print(f"✅ 完成! 共 {total} 张图表")
    print(f"  📄 data.json:      {os.path.join(out,'data.json')}")
    print(f"  📋 summary.json:   {summary_path}")
    print(f"  📸 输出目录:       {out}")
    print(f"{'='*60}")

    if total == 0:
        print("  ⚠ 未生成任何图表")

    # 输出摘要 JSON 到 stdout（主模型可解析）
    print("\n__SUMMARY_BEGIN__")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    print("__SUMMARY_END__")

    # HTML 报告由主模型分析完成后生成并写入 {out}/report.html
    # 脚本只负责数据采集+画图，不生成报告


def _generate_data_html(summary, html_path):
    """生成数据概览 HTML（含图表+数据），脚本自动生成并在浏览器中打开。"""
    import html as _html_mod

    code = summary.get("stock_code", "")
    name = summary.get("stock_name") or code
    market = summary.get("market", "")
    images = summary.get("images", {})
    data = summary.get("data", {})
    fetch_time = summary.get("fetch_time", "")
    tc = summary.get("text_charts") or {}

    def esc(s):
        if not s:
            return ""
        return _html_mod.escape(str(s))

    # 图片列表
    img_order = [
        "kline",
        "kline_weekly",
        "kline_monthly",
        "kline_intraday",
        "valuation",
        "capital_flow",
        "macro",
        "adr_premium",
        "financials_trend",
    ]
    img_labels_map = {
        "kline": "日K线图",
        "kline_weekly": "周K线图",
        "kline_monthly": "月K线图",
        "kline_intraday": "分时图",
        "valuation": "估值图",
        "capital_flow": "资金流向图",
        "macro": "宏观环境图",
        "adr_premium": "ADR溢价图",
        "financials_trend": "营收趋势图",
    }
    img_items = []
    for key in img_order:
        path = images.get(key)
        if path and os.path.exists(path):
            img_items.append((img_labels_map.get(key, key), path))
    for key, path in images.items():
        if path and os.path.exists(path) and key not in img_order:
            img_items.append((key.replace("_", " ").title(), path))

    from io import StringIO

    buf = StringIO()
    w = buf.write

    # === HTML HEAD ===
    w('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n')
    w(
        '<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    )
    w("<title>" + esc(name) + " (" + esc(code) + ") \u2014 数据概览</title>\n<style>\n")
    w("*{margin:0;padding:0;box-sizing:border-box;}\n")
    w(
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.8;background:#f0f2f5;color:#333;}\n'
    )
    w(".container{max-width:920px;margin:0 auto;padding:20px;}\n")
    w(
        ".card{background:white;border-radius:12px;padding:36px;box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-bottom:20px;}\n"
    )
    w(
        "h1{font-size:24px;color:#1a1a1a;border-bottom:3px solid #1e88e5;padding-bottom:10px;}\n"
    )
    w(".meta{color:#888;font-size:13px;margin-bottom:28px;}\n")
    w(
        "h2{font-size:18px;color:#1e88e5;margin-top:32px;margin-bottom:14px;padding-left:12px;border-left:4px solid #1e88e5;}\n"
    )
    w("table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13px;}\n")
    w("th,td{border:1px solid #e8eaed;padding:10px 12px;text-align:left;}\n")
    w("th{background:#1e88e5;color:white;font-weight:600;}\n")
    w("tr:nth-child(even){background:#f8f9fa;}\n")
    w(
        ".chart-box{text-align:center;margin:22px 0;background:#fafbfc;border:1px solid #e8eaed;border-radius:8px;padding:18px;}\n"
    )
    w(".chart-box img{max-width:100%;height:auto;border-radius:6px;}\n")
    w(".chart-caption{color:#888;font-size:13px;margin-top:10px;}\n")
    w(
        '.sparkline-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 20px;margin:20px 0;font-family:"SF Mono",Monaco,monospace;font-size:17px;letter-spacing:2px;text-align:center;}\n'
    )
    w(".news-item{border-bottom:1px solid #f0f0f0;padding:12px 0;}\n")
    w(".news-item:last-child{border:none;}\n")
    w(".news-title{font-weight:600;font-size:14px;color:#1a1a1a;}\n")
    w(".news-meta{color:#999;font-size:12px;margin:3px 0;}\n")
    w(".news-content{color:#666;font-size:13px;margin-top:4px;line-height:1.6;}\n")
    w(
        ".hint{background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);border:1px solid #bfdbfe;border-radius:8px;padding:18px 22px;margin-top:28px;font-size:13px;color:#1e40af;line-height:1.7;}\n"
    )
    w(
        ".footer{text-align:center;color:#aaa;font-size:12px;margin-top:24px;padding-top:16px;border-top:1px solid #e8eaed;}\n"
    )
    w(
        ".empty{color:#999;font-style:italic;padding:20px;text-align:center;background:#fafbfc;border-radius:6px;margin:10px 0;}\n"
    )
    w('</style>\n</head>\n<body>\n<div class="container">\n<div class="card">\n')

    # 标题
    w("<h1>📊 " + esc(name) + " (" + esc(code) + ") 数据概览</h1>\n")
    w(
        '<div class="meta"><strong>采集时间：</strong>'
        + fetch_time[:19]
        + " &nbsp;|&nbsp; <strong>市场：</strong>"
        + market.upper()
        + " &nbsp;|&nbsp; <strong>状态：</strong>原始数据采集完成，待主模型分析</div>\n"
    )

    # 文本折线图
    sp = tc.get("sparkline_60d") or tc.get("sparkline_20d") or ""
    if sp:
        w('<div class="sparkline-box">近期走势：' + esc(sp) + "</div>\n")

    # 图表
    w("<h2>📈 图表</h2>\n")
    if img_items:
        for label, path in img_items:
            w(
                '<div class="chart-box"><img src="file://'
                + path
                + '" alt="'
                + label
                + '" onerror="this.onerror=null;this.parentElement.style.display=\'none\'">'
                + '<div class="chart-caption">'
                + label
                + "</div></div>\n"
            )
    else:
        w('<p class="empty">本次未生成图表</p>\n')

    # 基本面
    w("<h2>💰 基本面数据</h2>\n")
    fin = data.get("financials") or {}
    fin_rows = ""
    if isinstance(fin, dict):
        for k, v in list(fin.items())[:15]:
            if v is not None and str(v).strip() and not str(v).startswith("{"):
                fin_rows += (
                    "<tr><td>" + esc(k) + "</td><td>" + esc(str(v)) + "</td></tr>"
                )
    if fin_rows:
        w("<table><tr><th>指标</th><th>数值</th></tr>" + fin_rows + "</table>\n")
    else:
        w('<p class="empty">未获取到基本面数据</p>\n')

    # 技术指标
    w("<h2>📐 技术指标</h2>\n")
    tech = data.get("technicals") or {}
    tech_rows = ""
    if isinstance(tech, dict):
        for k, v in list(tech.items())[:12]:
            if v is not None:
                tech_rows += (
                    "<tr><td>" + esc(k) + "</td><td>" + esc(str(v)) + "</td></tr>"
                )
    if tech_rows:
        w("<table><tr><th>指标</th><th>数值</th></table>" + tech_rows + "</table>\n")
    else:
        w('<p class="empty">未获取到技术指标</p>\n')

    # 资金流向
    w("<h2>💵 资金流向</h2>\n")
    mcf = data.get("main_capital_flow") or {}
    if isinstance(mcf, dict) and mcf.get("total_main_net_inflow") is not None:
        total = mcf.get("total_main_net_inflow", 0)
        days = mcf.get("consecutive_days", 0)
        direction = mcf.get("direction", "")
        w(
            f"<p><strong>{esc(direction)}:</strong> {total/1e8:.2f}亿 | 连续{days}天</p>\n"
        )
    cap = data.get("capital_flow_summary") or {}
    if isinstance(cap, dict) and cap:
        w(
            f'<p><strong>方向:</strong> {esc(cap.get("direction","N/A"))} | <strong>连续:</strong> {str(cap.get("consecutive_days","N/A"))}天</p>\n'
        )
    if (not mcf) and (not cap):
        w('<p class="empty">未获取到资金流数据</p>\n')

    # 研报
    w("<h2>📑 券商研报（最新）</h2>\n")
    rpt_rows = ""
    for r in (data.get("analyst_reports") or [])[:6]:
        rpt_rows += (
            "<tr><td>"
            + esc(r.get("org", ""))
            + "</td><td>"
            + esc(r.get("rating", ""))
            + "</td><td>"
            + esc(r.get("title", ""))
            + "</td><td>"
            + str(r.get("date", ""))
            + "</td></tr>"
        )
    if rpt_rows:
        w(
            "<table><tr><th>机构</th><th>评级</th><th>标题</th><th>日期</th></tr>"
            + rpt_rows
            + "</table>\n"
        )
    else:
        w('<p class="empty">未获取到研报数据</p>\n')

    # 新闻
    w("<h2>📰 近期新闻</h2>\n")
    news_divs = ""
    for n in (data.get("cls_news") or [])[:10]:
        title = n.get("title", "")
        date = str(n.get("date", ""))[:16]
        source = n.get("source", "")
        content_preview = (n.get("content") or "")[:120]
        news_divs += (
            '<div class="news-item"><div class="news-title">'
            + esc(title)
            + '</div><div class="news-meta">'
            + date
            + " · "
            + esc(source)
            + '</div><div class="news-content">'
            + esc(content_preview)
            + "...</div></div>"
        )
    if news_divs:
        w(news_divs + "\n")
    else:
        w('<p class="empty">未获取到新闻</p>\n')

    # 提示 + footer
    w(
        '<div class="hint"><strong>💡 下一步：</strong>多模态主模型将基于以上数据和图片，<br>'
    )
    w("输出完整的分析报告到聊天窗口中。<br>")
    w('如需导出 <strong>PDF 报告</strong>，请在聊天中回复"导出 PDF"。</div>\n')
    w(
        '<div class="footer">数据由 stock-analyst skill 自动采集 · '
        + fetch_time[:19]
        + "</div>\n"
    )
    w("</div></div></body></html>\n")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())


if __name__ == "__main__":
    main()
