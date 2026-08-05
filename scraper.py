import base64
from datetime import datetime, timezone, timedelta
import html
import os
import re
import time
import cloudscraper
from bs4 import BeautifulSoup

TARGET_URL = "https://yfamilys.com/subscribe"

BEIJING_TZ = timezone(timedelta(hours=8))

SUB_APIS = [
    "https://api.v1.mk/sub",
    "https://url.v1.mk/sub",
    "https://sub.id9.cc/sub",
]

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

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

SUB_CLIENT_HEADERS = {
    "User-Agent": "ClashMeta/v1.16.0 v2rayN/6.23"
}

# ===============================
# 安全写文件
# ===============================
def safe_write(filename, content):
    tmp = filename + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, filename)

# ===============================
# README 更新
# ===============================
def update_readme(raw_content):
    bt = "```"
    update_time = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S (UTC+8)")
    
    if raw_content.startswith("http"):
        display = raw_content
    else:
        count = len([x for x in raw_content.splitlines() if x.strip()])
        display = f"已成功抓取 {count} 条节点"

    content = f"""# 🚀 BestSub 自动订阅更新
自动抓取 yfamilys 最新订阅，转换：Clash / V2Ray。

---

## Clash订阅
{bt}text
https://raw.githubusercontent.com/zhulinghuanyu/BestSub/main/clash.yaml
{bt}

## V2Ray订阅
{bt}text
https://raw.githubusercontent.com/zhulinghuanyu/BestSub/main/v2ray.txt
{bt}

## 原始订阅
{bt}text
https://raw.githubusercontent.com/zhulinghuanyu/BestSub/main/links.txt
{bt}

---

更新时间:
{bt}text
{update_time}
{bt}

当前状态:
{bt}text
{display}
{bt}
"""

    old = ""
    if os.path.exists("README.md"):
        with open("README.md", encoding="utf-8") as f:
            old = f.read()

    if old != content:
        safe_write("README.md", content)
        print("📝 README 更新")
    else:
        print("README 无变化")

# ===============================
# 请求重试
# ===============================
def request_retry(scraper, url, **kwargs):
    for i in range(3):
        try:
            res = scraper.get(url, **kwargs)
            if res.status_code == 200:
                return res
        except Exception as e:
            print(f"请求失败 {i+1}/3:", e)
            time.sleep(3)
    raise Exception(f"请求失败:{url}")

# ===============================
# 判断订阅 URL
# ===============================
def is_valid_sub_url(url):
    clean_url = url.lower().split("#")[0]
    if any(x in clean_url for x in EXCLUDE_KEYWORDS):
        return False
    
    if "[yfamilys.com/subscribe/](https://yfamilys.com/subscribe/)" in clean_url and clean_url.rstrip('/') != "[https://yfamilys.com/subscribe](https://yfamilys.com/subscribe)":
        return True
    
    keys = ["sub", "token", "subscribe", "clash", "v2ray", "node", ".yaml", ".txt"]
    return any(x in clean_url for x in keys)

# ===============================
# 转换订阅
# ===============================
def convert_sub(scraper, target, raw_input):
    timestamp = int(time.time())
    
    if not raw_input.startswith("http"):
        node_lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
        sub_param = "|".join(node_lines)
    else:
        sub_param = raw_input

    for api in SUB_APIS:
        try:
            print(f"🔄 尝试转换 API: {api} -> {target}")
            params = {
                "target": target,
                "url": sub_param,
                "insert": "false",
                "_t": timestamp,
            }
            res = scraper.get(api, params=params, headers=DEFAULT_HEADERS, timeout=30)
            if res.status_code != 200:
                continue
            text = res.text.strip()
            if "<html" in text.lower():
                continue
            if target == "clash":
                if "proxies:" in text and len(text) > 100:
                    return text
            if target == "v2ray":
                if len(text) > 50:
                    return text
        except Exception as e:
            print("API 转换异常:", e)
    return None

# ===============================
# 主抓取逻辑
# ===============================
def fetch_links():
    print("🌐 请求 yfamilys 网页...")
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True
        }
    )
    
    response = request_retry(
        scraper,
        TARGET_URL,
        headers=DEFAULT_HEADERS,
        timeout=30
    )
    html_text = html.unescape(response.text)
    extracted = None

    # 1. 优先匹配节点协议格式
    node_pattern = (
        r"(?:vmess|vless|trojan|ss|ssr|"
        r"hysteria|hysteria2|hy2|tuic)"
        r"://[^\s<\"'>]+"
    )
    nodes = re.findall(node_pattern, html_text, re.I)
    if nodes:
        nodes = list(dict.fromkeys(nodes))
        extracted = "\n".join(nodes)
        print(f"✅ 提取到 {len(nodes)} 个独立节点")
    else:
        # 2. 匹配 yfamilys 专用动态订阅链接（排除主页路径）
        pattern = r"https://yfamilys\.com/subscribe/[A-Za-z0-9_\-?=&]+"
        results = re.findall(pattern, html_text)
        # 过滤掉末尾无 Token 的路径
        valid_links = [r for r in results if r.rstrip('/') != "[https://yfamilys.com/subscribe](https://yfamilys.com/subscribe)"]
        if valid_links:
            extracted = valid_links[0]
            print("✅ 提取到动态订阅链接:", extracted)
        else:
            # 3. 备用 HTML 节点解析
            soup = BeautifulSoup(html_text, "html.parser")
            urls = [a["href"] for a in soup.find_all("a", href=True)]
            urls += re.findall(r"https?://[^\s<\"'>]+", html_text)
            for u in dict.fromkeys(urls):
                if is_valid_sub_url(u):
                    extracted = u
                    break

    if not extracted:
        raise Exception("❌ 未在页面中查找到有效节点或动态链接")

    now = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S (UTC+8)")
    safe_write("links.txt", extracted)

    # -----------------------------
    # V2Ray 节点更新逻辑
    # -----------------------------
    v2ray_content = None
    if extracted.startswith("http"):
        # 优化：使用客户端 UA 直连获取订阅节点内容
        try:
            print("⬇️ 正在直连拉取 V2Ray 订阅节点...")
            direct_res = scraper.get(extracted, headers=SUB_CLIENT_HEADERS, timeout=15)
            if direct_res.status_code == 200 and len(direct_res.text.strip()) > 30 and "<html" not in direct_res.text.lower():
                v2ray_content = direct_res.text.strip()
                print("✅ 直连成功获取 V2Ray 内容")
        except Exception as e:
            print(f"⚠️ 直连拉取失败，尝试通过 API 转换: {e}")

        # 若直连失败则尝试 API 转换
        if not v2ray_content:
            v2ray_content = convert_sub(scraper, "v2ray", extracted)
            
        if not v2ray_content:
            raise Exception("❌ V2Ray 内容获取及转换均失败")
            
        # 修复：保持内容纯净，不写入 // 注释头，保障客户端正常解析
        safe_write("v2ray.txt", v2ray_content)
    else:
        # 如果抓到的是纯节点明文，直接 Base64 编码保存
        data = base64.b64encode(extracted.encode()).decode()
        safe_write("v2ray.txt", data)
    print("✅ v2ray.txt 更新完成")

    # -----------------------------
    # Clash 订阅更新逻辑
    # -----------------------------
    clash_content = convert_sub(scraper, "clash", extracted)
    if not clash_content:
        raise Exception("❌ Clash 配置转换失败")
    safe_write("clash.yaml", f"# Updated: {now}\n" + clash_content)
    print("✅ clash.yaml 更新完成")

    # 更新 README
    update_readme(extracted)
    print("🎉 所有任务执行完成！")

if __name__ == "__main__":
    fetch_links()
