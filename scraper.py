import base64
import html
import re
import time
import os
import cloudscraper
from bs4 import BeautifulSoup

TARGET_URL = "https://yfamilys.com/subscribe"

EXCLUDE_KEYWORDS = [
    "cloudflareinsights.com",
    "google-analytics.com",
    "googletagmanager.com",
    ".js",
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".ico",
    ".svg",
    "github.com",
    "githubusercontent.com",
]

# 在线订阅转换接口
SUB_APIS = [
    "https://api.v1.mk/sub",
    "https://url.v1.mk/sub",
]

# ===============================
# 更新 README
# ===============================

def update_readme(raw_content):
    bt = "```"
    if raw_content.startswith("http://") or raw_content.startswith("https://"):
        display_raw = raw_content
    else:
        node_count = len(
            [
                line
                for line in raw_content.splitlines()
                if line.strip()
            ]
        )
        display_raw = (
            f"已成功抓取并整合 {node_count} 条最新节点数据"
        )

    readme_content = f"""# 🚀 BestSub - 自动订阅更新

本项目自动抓取 yfamilys 最新订阅，并自动转换 Clash / V2Ray 格式。

---

## Clash 用户

{bt}text
https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/clash.yaml
{bt}

---

## V2Ray 用户

{bt}text
https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/v2ray.txt
{bt}

---

## 原始订阅链接

{bt}text
https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/links.txt
{bt}

---

## 当前抓取信息

{bt}text
{display_raw}
{bt}

---

自动更新周期：15分钟

"""

    # 防止无变化重复提交
    if os.path.exists("README.md"):
        with open(
            "README.md",
            encoding="utf-8"
        ) as f:
            old = f.read()
        if old == readme_content:
            print("README 无变化")
            return

    with open(
        "README.md",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            readme_content
        )
    print("📝 README 更新完成")

# ===============================
# 判断订阅链接
# ===============================
def is_valid_sub_url(url):
    url_lower = url.lower().split("#")[0]

    if any(
        kw in url_lower
        for kw in EXCLUDE_KEYWORDS
    ):
        return False

    # yfamilys 动态订阅
    if "yfamilys.com/subscribe/" in url_lower:
        return True

    features = [
        "sub",
        "token",
        "subscribe",
        "clash",
        "v2ray",
        "node",
        ".txt",
        ".yaml",
    ]
    return any(
        x in url_lower
        for x in features
    )

# ===============================
# 在线转换
# ===============================
def convert_sub(
        scraper,
        target,
        target_url
):

    timestamp = int(time.time())
    
    for api in SUB_APIS:
        try:
            params = {
                "target": target,
                "url": target_url,
                "insert": "false",
                "_t": timestamp,
            }
            print(
                f"🔄 {api} 转换 {target}"
            )
            res = scraper.get(
                api,
                params=params,
                timeout=25
            )
            if res.status_code == 200:
                text = res.text
                if target == "clash":
                    if (
                        "proxies:" in text
                        or
                        "proxy-groups:" in text
                    ):
                        return text
                if target == "v2ray":

                    if len(text.strip()) > 20:
                        return text
        except Exception as e:
            print(
                "转换失败:",
                e
            )
    return None

# ===============================
# 抓取入口
# ===============================
def fetch_links():
    print(
        "🌐 请求 yfamilys..."
    )
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
        }
    )
    try:
        response = scraper.get(
            TARGET_URL,
            timeout=30
        )
        response.raise_for_status()
        response.encoding = (
            response.apparent_encoding
            or
            "utf-8"
        )
        html_text = html.unescape(
            response.text
        )
    except Exception as e:
        print(
            "请求失败:",
            e
        )
        return
    extracted_content = None

    # ==========================
    # 1. 找节点
    # ==========================
    node_pattern = (
        r"(?:vmess|vless|trojan|ss|ssr|"
        r"hysteria|hysteria2|hy2|tuic)"
        r"://[^\s<\"'>]+"
    )

    node_matches = re.findall(
        node_pattern,
        html_text,
        re.I
    )

    if node_matches:
        node_matches = list(
            dict.fromkeys(node_matches)
        )
        extracted_content = "\n".join(
            node_matches
        )
        print(
            f"找到 {len(node_matches)} 个节点"
        )
    else:

        # ======================
        # 2. 找 yfamilys订阅
        # ======================
        yf_pattern = (
            r"https://yfamilys\.com/"
            r"subscribe/[A-Za-z0-9]+"
        )
        yf = re.findall(
            yf_pattern,
            html_text
        )
        if yf:
            extracted_content = yf[0]
            print(
                "找到 yfamilys订阅:",
                extracted_content
            )
        else:
            soup = BeautifulSoup(
                html_text,
                "html.parser"
            )
            urls = []
            for a in soup.find_all(
                "a",
                href=True
            ):
                urls.append(
                    a["href"]
                )
            urls.extend(
                re.findall(
                    r"https?://[^\s<\"'>]+",
                    html_text
                )
            )
            
            for url in list(
                dict.fromkeys(urls)
            ):
                if url.rstrip("/") == TARGET_URL:
                    continue
                if is_valid_sub_url(url):
                    extracted_content = url
                    break

    if not extracted_content:
        print(
            "❌ 没找到订阅"
        )
        return

    print(
        "✅ 提取:",
        extracted_content[:100]
    )

    is_url = (
        extracted_content.startswith(
            "http://"
        )
        or
        extracted_content.startswith(
            "https://"
        )
    )

    # 保存原始链接
    with open(
        "links.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            extracted_content
        )

    # ==========================
    # V2ray
    # ==========================
    if is_url:
        v2ray = convert_sub(
            scraper,
            "v2ray",
            extracted_content
        )
        if v2ray:
            with open(
                "v2ray.txt",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(v2ray)
            print(
                "✅ v2ray完成"
            )
    else:
        data = base64.b64encode(
            extracted_content.encode()
        ).decode()
        with open(
            "v2ray.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(data)

    # ==========================
    # Clash
    # ==========================
    clash = convert_sub(
        scraper,
        "clash",
        extracted_content
    )
    if clash:
        with open(
            "clash.yaml",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(clash)
        print(
            "✅ clash完成"
        )
    else:
        print(
            "⚠️ clash转换失败"
        )
    update_readme(
        extracted_content
    )

if __name__ == "__main__":

    fetch_links()
