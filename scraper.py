import re
import cloudscraper

TARGET_URL = "https://yfamilys.com/subscribe"

# 过滤黑名单
EXCLUDE_KEYWORDS = [
    "cloudflareinsights.com",
    "google-analytics.com",
    "googletagmanager.com",
    ".js", ".css", ".png", ".jpg", ".jpeg", ".ico", ".svg"
]

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

    extracted_urls = []

    if html_text:
        # 正则匹配所有节点/订阅协议链接
        raw_url_pattern = r'(?:https?|clash|v2ray|sub|vmess|vless|trojan|ss|ssr|hysteria2|hy2)://[^\s<"\'>]+'
        matches = re.findall(raw_url_pattern, html_text)
        
        for url in matches:
            # 过滤垃圾链接与原页面链接
            if any(kw in url.lower() for kw in EXCLUDE_KEYWORDS):
                continue
            if url in (TARGET_URL, f"{TARGET_URL}/"):
                continue

            # 去重保存纯 URL
            if url not in extracted_urls:
                extracted_urls.append(url)

    print(f"✅ 抓取完成！共提取到 {len(extracted_urls)} 条链接")

    # 直接将纯链接写入 links.txt（一行一个链接）
    with open("links.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(extracted_urls))

if __name__ == "__main__":
    fetch_links()
