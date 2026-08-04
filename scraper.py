import json
import re
import cloudscraper
from bs4 import BeautifulSoup

TARGET_URL = "https://yfamilys.com/subscribe"

def fetch_links():
    print("🌐 正在请求目标页面...")
    # 使用 cloudscraper 绕过 Cloudflare 防火墙
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
        print(f"📄 成功获取页面，内容长度: {len(html_text)} 字符")
    except Exception as e:
        print(f"❌ 网页请求失败: {e}")
        html_text = ""

    extracted_data = []
    found_urls = set()

    if html_text:
        # 1. 解析 HTML 标签中的 <a> 链接
        soup = BeautifulSoup(html_text, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            text = a_tag.get_text(strip=True) or "未命名链接"
            if href and href not in found_urls and href.startswith(('http://', 'https://', 'clash://', 'v2ray://', 'sub://', 'vmess://', 'vless://', 'trojan://', 'ss://', 'hy2://')):
                extracted_data.append({"text": text, "url": href})
                found_urls.add(href)

        # 2. 全局正则提取文本中的节点/订阅链接（包含写在文本区域、代码块中的链接）
        raw_url_pattern = r'(?:https?|clash|v2ray|sub|vmess|vless|trojan|ss|ssr|hysteria2|hy2)://[^\s<"\'>]+'
        matches = re.findall(raw_url_pattern, html_text)
        
        for url in matches:
            # 过滤常见的图片/样式静态资源
            if url not in found_urls and not re.search(r'\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2)(\?.*)?$', url, re.I):
                extracted_data.append({"text": "提取节点/订阅", "url": url})
                found_urls.add(url)

    print(f"✅ 抓取完成！共提取到 {len(extracted_data)} 条有效链接")

    # 保存至 JSON
    with open("links.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_links()
