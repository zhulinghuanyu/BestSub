import re
import cloudscraper

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


def update_readme(raw_url):
    """自动重写并更新 README.md 文件"""
    bt = "```"
    readme_content = f"""# 🚀 BestSub - 每日订阅链接自动更新

本项目**自动抓取**最新订阅节点并完成格式转换，请根据你使用的代理软件选择对应的订阅地址：

---

## ⚡ 客户端订阅链接（推荐使用）

### 🐱 Clash / Clash Verge / Stash 用户
请复制以下链接粘贴到软件的“配置/订阅”中：
{bt}text
[https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/clash.yaml](https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/clash.yaml)
{bt}

---

### 🚀 V2rayN / V2rayNG / Shadowrocket 用户
请复制以下链接粘贴到软件的“订阅设置”中：
{bt}text
[https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/v2ray.txt](https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/v2ray.txt)
{bt}

---

## 🔗 原始动态链接信息

* **TXT 文本订阅 (CDN 加速)**：
  {bt}text
  [https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/links.txt](https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/links.txt)
  {bt}

* **📌 当前抓取到的最新原始动态订阅链接（实时更新）**：
  {bt}text
  {raw_url}
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
        "hysteria2://",
        "hy2://",
    )
    if url_lower.startswith(node_protocols):
        return True

    # 2. 如果是当前站点的链接，必须包含订阅特征词，排除关于我们、首页等普通页面
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
        html_text = response.text
    except Exception as e:
        print(f"❌ 网页请求失败: {e}")
        return

    extracted_url = None

    if html_text:
        # 第一优先级：匹配明文节点列表 (vmess, vless, trojan 等)
        node_pattern = r"(?:vmess|vless|trojan|ss|ssr|hysteria2|hy2)://[^\s<\"'>]+"
        node_matches = re.findall(node_pattern, html_text, re.IGNORECASE)

        if node_matches:
            extracted_url = "\n".join(node_matches)
            print(f"✅ 成功提取到 {len(node_matches)} 条节点数据！")
        else:
            # 第二优先级：匹配动态订阅 URL
            raw_url_pattern = r"https?://[^\s<\"'>]+"
            matches = re.findall(raw_url_pattern, html_text)

            for url in matches:
                if url.rstrip("/") == TARGET_URL.rstrip("/"):
                    continue
                if is_valid_sub_url(url):
                    extracted_url = url
                    break

    if not extracted_url:
        print("❌ 未找到有效的订阅链接或节点信息")
        return

    print(f"✅ 抓取成功！获取到的源内容前缀: {extracted_url[:80]}...")

    # 1. 保存纯文本源链接 (links.txt)
    with open("links.txt", "w", encoding="utf-8") as f:
        f.write(extracted_url)

    # 2. 转换生成 Clash 配置文件 (使用 params 自动处理参数转义 + 内容校验)
    try:
        print("🔄 正在生成 Clash 配置文件...")
        sub_api = "https://api.v1.mk/sub"
        params = {"target": "clash", "url": extracted_url, "insert": "false"}
        res_clash = scraper.get(sub_api, params=params, timeout=30)

        # 校验：返回 HTTP 200 且内容包含 Clash 节点特征关键字
        if res_clash.status_code == 200 and (
            "proxies:" in res_clash.text or "proxy-groups:" in res_clash.text
        ):
            with open("clash.yaml", "w", encoding="utf-8") as f:
                f.write(res_clash.text)
            print("✅ clash.yaml 生成成功！")
        else:
            print("⚠️ Clash 转换返回数据无效，取消覆盖现有配置文件")
    except Exception as e:
        print(f"⚠️ Clash 格式转换失败: {e}")

    # 3. 转换生成 V2ray 专属订阅文件 (v2ray.txt)
    try:
        print("🔄 正在生成 V2ray 订阅格式...")
        sub_api = "https://api.v1.mk/sub"
        params = {"target": "v2ray", "url": extracted_url}
        res_v2ray = scraper.get(sub_api, params=params, timeout=30)

        if res_v2ray.status_code == 200 and len(res_v2ray.text.strip()) > 20:
            with open("v2ray.txt", "w", encoding="utf-8") as f:
                f.write(res_v2ray.text)
            print("✅ v2ray.txt 生成成功！")
        else:
            print("⚠️ V2ray 转换返回数据为空，取消覆盖现有配置文件")
    except Exception as e:
        print(f"⚠️ V2ray 格式转换失败: {e}")

    # 4. 自动写入/更新 README.md
    update_readme(extracted_url)


if __name__ == "__main__":
    fetch_links()
