import json
import re
import requests
from bs4 import BeautifulSoup

# 目标 URL
TARGET_URL = "https://yfamilys.com/subscribe"

# 伪装请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

def fetch_links():
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        
        extracted_data = []

        # 1. 抓取所有 <a> 标签中的 href 链接
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            text = a_tag.get_text(strip=True)
            if href:
                extracted_data.append({
                    "type": "link",
                    "text": text,
                    "url": href
                })

        # 2. 匹配文本中的通用 URL 格式（如 Clash/V2Ray/订阅等节点链接）
        urls_in_text = re.findall(r'https?://[^\s<"\']+', response.text)
        for url in set(urls_in_text):
            extracted_data.append({
                "type": "raw_url",
                "url": url
            })

        print(f"成功提取到 {len(extracted_data)} 条数据")

        # 保存结果为 JSON 文件
        with open("links.json", "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"爬取失败: {e}")

if __name__ == "__main__":
    fetch_links()
