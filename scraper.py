import html
import re
import time
import cloudscraper
from bs4 import BeautifulSoup

TARGET_URL = "https://yfamilys.com/subscribe"

# 过滤不相关的域名和文件后缀
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

# 备用转换 API 列表（解决单节点限流或缓存不更新问题）
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
        node_count = len(raw_content.splitlines())
        display_raw = f"已成功抓取并整合 {node_count} 条最新节点数据（已自动同步至上方订阅地址）"

    readme_content = f"""# 🚀 BestSub - 每日订阅链接自动更新

本项目**自动抓取**最新订阅节点并完成格式转换，请根据你使用的代理软件选择对应的订阅地址：

---

## ⚡ 客户端订阅链接

### 🐱 Clash / Clash Verge / Stash 用户
请复制以下链接粘贴到软件的“配置/订阅”中：
{bt}text
[https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/clash.yaml](https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/clash.yaml)
{bt}

---

### 🚀 V2rayN / V2rayNG / Shadowrocket 用户
请复制以下链接粘贴到软件的“订阅设置”中：
{bt}text
[https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/v2ray.txt](https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/v2ray.txt)
{bt}

---

## 🔗 原始动态链接信息

* **TXT 文本订阅**：
  {bt}text
  [https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/links.txt](https://github.com/zhulinghuanyu/BestSub/raw/refs/heads/main/links.txt)
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
    url_lower = url.lower()

    if any(kw in url_lower for kw in EXCLUDE_KEYWORDS):
        return False

    # 1. 节点协议前缀直接放行
    node_protocols = (
        "vmess://",
        "vless://",
        "trojan://",
        "ss://",
        "ssr://",
        "hysteria://",
        "hysteria2://",
        "hy2://",
        "tuic://",
    )
    if url_lower.startswith(node_protocols):
        return True

    # 2. 如果是当前站点的链接，必须包含订阅特征词
    if "yfamilys.com" in url_lower:
        if not any(
            k in url_lower
            for k in ["token=", "sub", "subscribe", "download", "clash", "v2ray"]
        ):
            return False

    # 3. 普通 HTTP(S) 链接需包含常见订阅特征词
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


def convert_sub(scraper, target, url_param):
    """通用订阅转换函数，包含时间戳防缓存与多节点容错机制"""
    timestamp = int(time.time())

    for api in SUB_APIS:
        try:
            params = {
                "target": target,
                "url": url_param,
                "insert": "false",
                "_t": timestamp,  # 传入当前时间戳破除转换站点的服务器缓存
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
        # 进行 HTML 反转义处理，防止 &amp; 导致 URL 损坏
        html_text = html.unescape(response.text)
    except Exception as e:
        print(f"❌ 网页请求失败: {e}")
        return

    extracted_content = None  # 用于写入 links.txt 的文本内容
    api_url_param = None      # 用于提交给 subconverter API 的 url 参数

    if html_text:
        # 第一优先级：匹配明文节点列表
        node_pattern = r"(?:vmess|vless|trojan|ss|ssr|hysteria|hysteria2|hy2|tuic)://[^\s<\"'>]+"
        node_matches = re.findall(node_pattern, html_text, re.IGNORECASE)

        if node_matches:
            # 保持顺序去重
            node_matches = list(dict.fromkeys(node_matches))
            extracted_content = "\n".join(node_matches)
            # 传给 API 时用 | 分隔，限制最大前 200 条节点防止 URL 溢出
            api_url_param = "|".join(node_matches[:200])
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
                    api_url_param = url
                    break

    if not extracted_content:
        print("❌ 未找到有效的订阅链接或节点信息")
        return

    print(f"✅ 抓取成功！内容前缀: {extracted_content[:80]}...")

    # 1. 保存纯文本源链接或节点列表 (links.txt)
    with open("links.txt", "w", encoding="utf-8") as f:
        f.write(extracted_content)

    # 2. 转换生成 Clash 配置文件
    clash_content = convert_sub(scraper, "clash", api_url_param)
    if clash_content:
        with open("clash.yaml", "w", encoding="utf-8") as f:
            f.write(clash_content)
        print("✅ clash.yaml 生成成功！")
    else:
        print("⚠️ 所有转换接口均未返回有效数据，保留现有 clash.yaml")

    # 3. 转换生成 V2ray 专属订阅文件 (v2ray.txt)
    v2ray_content = convert_sub(scraper, "v2ray", api_url_param)
    if v2ray_content:
        with open("v2ray.txt", "w", encoding="utf-8") as f:
            f.write(v2ray_content)
        print("✅ v2ray.txt 生成成功！")
    else:
        print("⚠️ 所有转换接口均未返回有效数据，保留现有 v2ray.txt")

    # 4. 自动写入/更新 README.md
    update_readme(extracted_content)


if __name__ == "__main__":
    fetch_links()
