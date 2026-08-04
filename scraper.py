import re
import cloudscraper

TARGET_URL = "[https://yfamilys.com/subscribe](https://yfamilys.com/subscribe)"

# 过滤黑名单（剔除 JS/图片/统计脚本等无用链接）
EXCLUDE_KEYWORDS = [
    "cloudflareinsights.com",
    "google-analytics.com",
    "googletagmanager.com",
    ".js", ".css", ".png", ".jpg", ".jpeg", ".ico", ".svg"
]

def update_readme(raw_url):
    """自动重写并更新 README.md 文件，将抓取的最新链接写入说明页"""
    bt = "```"  # 避免嵌入的代码框反引号打乱渲染
    readme_content = f"""# 🚀 BestSub - 每日订阅链接自动更新

本项目**自动抓取**最新订阅节点并完成格式转换，请根据你使用的代理软件选择对应的订阅地址：

---

## ⚡ 客户端订阅链接（推荐使用）

### 🐱 Clash / Clash Verge / Stash 用户
请复制以下链接粘贴到软件的“配置/订阅”中：
{bt}text
https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/clash.yaml
{bt}

---

### 🚀 V2rayN / V2rayNG / Shadowrocket 用户
请复制以下链接粘贴到软件的“订阅设置”中：
{bt}text
https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/v2ray.txt
{bt}

---

## 🔗 原始动态链接信息

* **TXT 文本订阅 (CDN 加速)**：
  {bt}text
  https://cdn.jsdelivr.net/gh/zhulinghuanyu/BestSub@main/links.txt
  {bt}

* **📌 当前抓取到的最新原始动态订阅链接（实时更新）**：
  {bt}text
  {raw_url}
  {bt}

---

💡 **提示**：系统会自动定期抓取并更新文件。如果遇到节点不可用，请在软件中手动点击“更新订阅”。
"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content.strip())
    print("📝 README.md 已成功同步更新！")


def fetch_links():
    print("🌐 正在请求目标页面...")
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    try:
        response = scraper.get(TARGET_URL, timeout=30)
        response.encoding = response.apparent_encoding or 'utf-8'
        html_text = response.text
    except Exception as e:
        print(f"❌ 网页请求失败: {e}")
        html_text = ""

    extracted_url = None

    if html_text:
        # 正则匹配目标链接
        raw_url_pattern = r'(?:https?|clash|v2ray|sub|vmess|vless|trojan|ss|ssr|hysteria2|hy2)://[^\s<"\'>]+'
        matches = re.findall(raw_url_pattern, html_text)
        
        for url in matches:
            if any(kw in url.lower() for kw in EXCLUDE_KEYWORDS):
                continue
            if url in (TARGET_URL, f"{TARGET_URL}/"):
                continue
            
            # 找到动态订阅链接
            extracted_url = url
            break

    if not extracted_url:
        print("❌ 未找到有效的订阅链接")
        return

    print(f"✅ 成功抓取到源链接: {extracted_url}")

    # 1. 保存纯文本源链接 (links.txt)
    with open("links.txt", "w", encoding="utf-8") as f:
        f.write(extracted_url)

    # 2. 转换生成 Clash 专属配置文件 (clash.yaml)
    try:
        print("🔄 正在生成 Clash 配置文件...")
        clash_api = f"https://api.v1.mk/sub?target=clash&url={extracted_url}&insert=false"
        res_clash = scraper.get(clash_api, timeout=20)
        if res_clash.status_code == 200:
            with open("clash.yaml", "w", encoding="utf-8") as f:
                f.write(res_clash.text)
            print("✅ clash.yaml 生成成功！")
    except Exception as e:
        print(f"⚠️ Clash 格式转换失败: {e}")

    # 3. 转换生成 V2ray 专属订阅文件 (v2ray.txt)
    try:
        print("🔄 正在生成 V2ray 订阅格式...")
        v2ray_api = f"https://api.v1.mk/sub?target=v2ray&url={extracted_url}"
        res_v2ray = scraper.get(v2ray_api, timeout=20)
        if res_v2ray.status_code == 200:
            with open("v2ray.txt", "w", encoding="utf-8") as f:
                f.write(res_v2ray.text)
            print("✅ v2ray.txt 生成成功！")
    except Exception as e:
        print(f"⚠️ V2ray 格式转换失败: {e}")

    # 4. 自动写入/更新 README.md
    update_readme(extracted_url)

if __name__ == "__main__":
    fetch_links()
