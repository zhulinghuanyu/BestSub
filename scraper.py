import json
import re
import cloudscraper

TARGET_URL = "https://yfamilys.com/subscribe"

# 需要过滤掉的垃圾域名和文件后缀
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

    extracted_data = []
    found_urls = set()

    if html_text:
        # 正则匹配所有 http(s) 以及节点协议链接
        raw_url_pattern = r'(?:https?|clash|v2ray|sub|vmess|vless|trojan|ss|ssr|hysteria2|hy2)://[^\s<"\'>]+'
        matches = re.findall(raw_url_pattern, html_text)
        
        for url in matches:
            # 1. 过滤掉包含黑名单关键词的链接（如 cloudflare 统计 JS）
            if any(kw in url.lower() for kw in EXCLUDE_KEYWORDS):
                continue
            
            # 2. 过滤掉页面本身的 URL
            if url in (TARGET_URL, f"{TARGET_URL}/"):
                continue

            # 3. 去重保存
            if url not in found_urls:
                extracted_data.append({
                    "text": "动态订阅链接" if "subscribe/" in url else "节点链接",
                    "url": url
                })
                found_urls.add(url)

    print(f"✅ 抓取完成！共提取到 {len(extracted_data)} 条有效订阅链接")

    # 保存结果
    with open("links.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_links()
