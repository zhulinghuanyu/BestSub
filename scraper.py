import base64
import html
import re
import time
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

SUB_APIS = [
    "https://api.v1.mk/sub",
    "https://sub.id9.cc/sub",
    "https://url.v1.mk/sub",
]


def update_readme(raw_content):
    """自动重写并更新 README.md 文件"""
    bt = "```"

    if raw_content.startswith("http://") or raw_content.startswith("https://"):
        display_raw = raw_content
    else:
        node_count = len([line for line in raw_content.splitlines() if line.strip()])
        display_raw = f"已成功抓取并整合 {node_count} 条最新节点数据（已自动同步至上方订阅地址）"

    readme_content = f"""# 🚀 BestSub - 每日订阅链接自动更新

本项目**自动抓取**最新订阅节点并完成格式转换，请根据你使用的代理软件选择对应的订阅地址：

---

## ⚡ 客户端订阅链接

### 🐱 Clash / Clash Verge / Stash 用户
复制以下链接粘贴到软件的“配置/订阅”中：
{bt}text
https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/clash.yaml
{bt}

---

### 🚀 V2rayN / V2rayNG / Shadowrocket 用户
复制以下链接粘贴到软件的“订阅设置”中：
{bt}text
https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/v2ray.txt
{bt}

---

## 🔗 原始动态链接信息

* **TXT 文本订阅**：
{bt}text
https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/links.txt
{bt}

* **📌 当前抓取到的最新原始数据信息**：
{bt}text
{display_raw}
{bt}

---

💡 **提示**：系统会自动定期抓取并更新文件。如果遇到节点不可用，请在软件中手动点击“更新订阅”。
"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content.strip() + "\n")
    print("📝 README.md 已成功同步更新！")


def is_valid_sub_url(url):
    """精确判断提取出的 URL 是否为合法的订阅链接"""
    url_lower = url.lower().split("#")[0]

    if any(kw in url_lower for kw in EXCLUDE_KEYWORDS):
        return False

    if "yfamilys.com" in url_lower:
        if not any(k in url_lower for k in ["token=", "sub=", "download", "clash", "v2ray"]):
            return False

    sub_features = [
        "sub",
        "token",
        "subscribe",
        "clash",
        "v2ray",
        "node",
        ".txt",
        ".yaml",
    ]
    return any(feat in url_lower for feat in sub_features)


def convert_sub(scraper, target, target_url):
    """通过线上 API 进行格式转换"""
    timestamp = int(time.time())

    for api in SUB_APIS:
        try:
            params = {
                "target": target,
                "url": target_url,
                "insert": "false",
                "_t": timestamp,
            }
            print(f"🔄 正在尝试通过 {api} 生成 {target} 格式...")
            res = scraper.get(api, params=params, timeout=25)

            if res.status_code == 200:
                text = res.text
                if target == "clash" and ("proxies:" in text or "proxy-groups:" in text):
                    return text
                elif target == "v2ray" and len(text.strip()) > 20:
                    return text
        except Exception as e:
            print(f"⚠️ 转换节点 {api} 响应失败: {e}")
            continue

    return None


def fetch_links():
    print("🌐 正在请求目标页面...")
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
        }
    )

    try:
        response = scraper.get(TARGET_URL, timeout=30)
        response.encoding = response.apparent_encoding or "utf-8"
        html_text = html.unescape(response.text)
    except Exception as e:
        print(f"❌ 网页请求失败: {e}")
        return

    extracted_content = None

    if html_text:
        # 第一优先级：匹配明文节点列表
        node_pattern = r"(?:vmess|vless|trojan|ss|ssr|hysteria|hysteria2|hy2|tuic)://[^\s<\"'>]+"
        node_matches = re.findall(node_pattern, html_text, re.IGNORECASE)

        if node_matches:
            node_matches = list(dict.fromkeys(node_matches))
            extracted_content = "\n".join(node_matches)
            print(f"✅ 成功提取到 {len(node_matches)} 条节点数据！")
        else:
            # 第二优先级：匹配动态订阅 URL
            soup = BeautifulSoup(html_text, "html.parser")
            candidate_urls = []

            for a in soup.find_all("a", href=True):
                candidate_urls.append(a["href"].strip())

            raw_url_pattern = r"https?://[^\s<\"'>]+"
            candidate_urls.extend(re.findall(raw_url_pattern, html_text))

            for url in list(dict.fromkeys(candidate_urls)):
                if url.rstrip("/") == TARGET_URL.rstrip("/"):
                    continue
                if is_valid_sub_url(url):
                    extracted_content = url
                    break

    if not extracted_content:
        print("❌ 未找到有效的订阅链接或节点信息")
        return

    print(f"✅ 抓取成功！内容前缀: {extracted_content[:80]}...")

    is_single_url = extracted_content.startswith("http://") or extracted_content.startswith("https://")

    # 1. 保存原始提取结果 (links.txt)
    with open("links.txt", "w", encoding="utf-8") as f:
        f.write(extracted_content)

    # 2. 生成 V2ray 订阅格式 (v2ray.txt)
    if is_single_url:
        print("🔄 抓取到的是单一链接，通过转换 API 生成 V2ray 格式...")
        v2ray_content = convert_sub(scraper, "v2ray", extracted_content)
        if v2ray_content:
            with open("v2ray.txt", "w", encoding="utf-8") as f:
                f.write(v2ray_content)
            print("✅ v2ray.txt 生成成功！")
        else:
            print("⚠️ V2ray 转换未返回有效数据，保留现有文件")
    else:
        v2ray_base64 = base64.b64encode(extracted_content.encode("utf-8")).decode("utf-8")
        with open("v2ray.txt", "w", encoding="utf-8") as f:
            f.write(v2ray_base64)
        print("✅ v2ray.txt 本地 Base64 编码成功！")

    # 3. 转换生成 Clash 配置文件 (clash.yaml)
    # 使用 Data URI 方式传输给转换接口，避免直接依赖尚未来得及提交至 GitHub 的远程路径
    if is_single_url:
        clash_target_url = extracted_content
    else:
        b64_nodes = base64.b64encode(extracted_content.encode("utf-8")).decode("utf-8")
        clash_target_url = f"data:text/plain;base64,{b64_nodes}"

    clash_content = convert_sub(scraper, "clash", clash_target_url)

    if clash_content:
        with open("clash.yaml", "w", encoding="utf-8") as f:
            f.write(clash_content)
        print("✅ clash.yaml 生成成功！")
    else:
        print("⚠️ Clash 转换接口未返回有效数据，保留现有 clash.yaml")

    # 4. 自动写入/更新 README.md
    update_readme(extracted_content)


if __name__ == "__main__":
    fetch_links()
