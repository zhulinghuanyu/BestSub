import json
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TARGET_URL = "https://yfamilys.com/subscribe"

def fetch_links():
    extracted_data = []
    
    with sync_playwright() as p:
        print("🚀 正在启动无头浏览器...")
        # 启动 Chromium 浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"🌐 正在打开页面: {TARGET_URL}")
        # 访问页面并等待网络空闲（页面数据加载完毕）
        page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
        
        # 额外等待 3 秒保证 JS 渲染彻底完成
        page.wait_for_timeout(3000)

        # 获取渲染后的完整 HTML 页面
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # 1. 抓取页面中的所有 <a> 标签超链接
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            text = a_tag.get_text(strip=True)
            if href and href.startswith(('http://', 'https://', 'clash://', 'v2ray://', 'sub://')):
                extracted_data.append({
                    "text": text or "未命名链接",
                    "url": href
                })

        # 2. 匹配页面文本中的节点协议（vmess/vless/ss/trojan/hy2 等及常规 URL）
        patterns = [
            r'(?:vmess|vless|ss|ssr|trojan|hysteria2|hy2)://[^\s<"\']+',
            r'https?://[^\s<"\']+'
        ]
        
        existing_urls = {item['url'] for item in extracted_data}
        for pattern in patterns:
            for match in re.findall(pattern, content):
                if match not in existing_urls:
                    extracted_data.append({
                        "text": "提取节点/订阅",
                        "url": match
                    })
                    existing_urls.add(match)

        browser.close()

    print(f"✅ 抓取完成！共提取到 {len(extracted_data)} 条链接数据")

    # 写入 JSON
    with open("links.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_links()
