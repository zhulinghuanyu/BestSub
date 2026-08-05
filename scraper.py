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
    "https://sub.id9.cc/sub",
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
            [line for line in raw_content.splitlines() if line.strip()]
        )
        display_raw = f"已成功抓取并整合 {node_count} 条最新节点数据"

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

    if os.path.exists("README.md"):
        with open("README.md", encoding="utf-8") as f:
            old = f.read()
        if old == readme_content:
            print("README 无变化")
            return

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("📝 README 更新完成")

# ===============================
# 判断订阅链接
# ===============================
def is_valid_sub_url(url):
    url_lower = url.lower().split("#")[0]

    if any(kw in url_lower for kw in EXCLUDE_KEYWORDS):
        return False

    if "[yfamilys.com/subscribe/](https://yfamilys.com/subscribe/)" in url_lower:
        return True

    features = [
        "sub", "token", "subscribe", "clash", 
        "v2ray", "node", ".txt", ".yaml"
    ]
    return any(x in url_lower for x in features)

# ===============================
# 在线转换
# ===============================
def convert_sub(scraper, target, target_url):
    timestamp = int(time.time())
    
    for api in SUB_APIS:
        try:
            params = {
                "target": target,
                "url": target_url,
                "insert": "false",
                "_t": timestamp,
            }
            print(f"🔄 使用 {api} 转换为 {target} 格式...")
            res = scraper.get(api, params=params, timeout=20)
            if res.status_code == 200:
                text = res.text
                if target == "clash":
                    if "proxies:" in text or "proxy-groups:" in text:
                        return text
                if target == "v2ray":
                    if len(text.strip()) > 20:
                        return text
        except Exception as e:
            print(f"转换节点 {api} 失败:", e)
    return None

# ===============================
# 抓取主程序
# ===============================
def fetch_links():
    print("🌐 请求 yfamilys...")
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
        }
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    try:
        response = scraper.get(TARGET_URL, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        html_text = html.unescape(response.text)
    except Exception as e:
        print("请求目标网站失败:", e)
        return

    extracted_content = None

    # 1. 优先匹配节点明文 (vmess://, vless:// 等)
    node_pattern = (
        r"(?:vmess|vless|trojan|ss|ssr|hysteria|hysteria2|hy2|tuic)"
        r"://[^\s<\"'>]+"
    )
    node_matches = re.findall(node_pattern, html_text, re.I)

    if node_matches:
        node_matches = list(dict.fromkeys(node_matches))
        extracted_content = "\n".join(node_matches)
        print(f"找到 {len(node_matches)} 个节点")
    else:
        # 2. 匹配 yfamilys 动态订阅链接
        yf_pattern = r"https://yfamilys\.com/subscribe/[A-Za-z0-9_-]+"
        yf = re.findall(yf_pattern, html_text)
        if yf:
            extracted_content = yf[0]
            print("找到 yfamilys 订阅链接:", extracted_content)
        else:
            # 3. 通用 HTML 超链接兜底提取
            soup = BeautifulSoup(html_text, "html.parser")
            urls = [a["href"] for a in soup.find_all("a", href=True)]
            urls.extend(re.findall(r"https?://[^\s<\"'>]+", html_text))
            
            for url in list(dict.fromkeys(urls)):
                if url.rstrip("/") == TARGET_URL:
                    continue
                if is_valid_sub_url(url):
                    extracted_content = url
                    break

    if not extracted_content:
        print("❌ 提取失败：未在页面找到任何有效订阅或节点")
        return

    print("✅ 提取成功:", extracted_content[:100])
    is_url = extracted_content.startswith("http://") or extracted_content.startswith("https://")

    # 当前时间戳，用于写入文件顶部触发 Git 提交变动
    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    # 保存原始提取内容
    with open("links.txt", "w", encoding="utf-8") as f:
        f.write(extracted_content)

    # ==========================
    # 生成 V2Ray 格式
    # ==========================
    if is_url:
        v2ray = convert_sub(scraper, "v2ray", extracted_content)
        if v2ray:
            # 在顶部加入时间戳注释，确保文本发生改动
            v2ray_content = f"// Updated at: {now_str}\n" + v2ray
            with open("v2ray.txt", "w", encoding="utf-8") as f:
                f.write(v2ray_content)
            print("✅ v2ray 转换完成")
    else:
        data = base64.b64encode(extracted_content.encode('utf-8')).decode('utf-8')
        with open("v2ray.txt", "w", encoding="utf-8") as f:
            f.write(data)
        print("✅ v2ray 节点Base64编码完成")

    # ==========================
    # 生成 Clash 格式
    # ==========================
    clash = convert_sub(scraper, "clash", extracted_content)
    if clash:
        # 在 YAML 顶部加入时间戳注释，确保文本发生改动
        clash_content = f"# Updated at: {now_str}\n" + clash
        with open("clash.yaml", "w", encoding="utf-8") as f:
            f.write(clash_content)
        print("✅ clash 转换完成")
    else:
        print("⚠️ clash 转换失败")

    update_readme(extracted_content)


if __name__ == "__main__":
    fetch_links()
