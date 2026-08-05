import base64
import html
import re
import time
import os
import cloudscraper
from bs4 import BeautifulSoup


TARGET_URL = "https://yfamilys.com/subscribe"


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


# ===============================
# 安全写文件
# ===============================

def safe_write(filename, content):

    tmp = filename + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)

    os.replace(tmp, filename)


# ===============================
# README
# ===============================

def update_readme(raw_content):

    bt = "```"

    update_time = time.strftime(
        "%Y-%m-%d %H:%M:%S UTC",
        time.gmtime()
    )


    if raw_content.startswith("http"):
        display = raw_content
    else:
        count = len(
            [
                x for x in raw_content.splitlines()
                if x.strip()
            ]
        )

        display = (
            f"已成功抓取 {count} 条节点"
        )


    content = f"""
# 🚀 BestSub 自动订阅更新


自动抓取 yfamilys 最新订阅。

自动转换：

- Clash
- V2Ray


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

        with open(
            "README.md",
            encoding="utf-8"
        ) as f:
            old = f.read()


    if old != content:

        safe_write(
            "README.md",
            content
        )

        print(
            "📝 README 更新"
        )

    else:

        print(
            "README 无变化"
        )



# ===============================
# 请求重试
# ===============================

def request_retry(
        scraper,
        url,
        **kwargs
):

    for i in range(3):

        try:

            res = scraper.get(
                url,
                **kwargs
            )

            return res


        except Exception as e:

            print(
                f"请求失败 {i+1}/3:",
                e
            )

            time.sleep(3)


    raise Exception(
        f"请求失败:{url}"
    )



# ===============================
# 判断订阅URL
# ===============================

def is_valid_sub_url(url):

    url = url.lower().split("#")[0]


    if any(
        x in url
        for x in EXCLUDE_KEYWORDS
    ):
        return False



    if "yfamilys.com/subscribe" in url:
        return True



    keys = [
        "sub",
        "token",
        "subscribe",
        "clash",
        "v2ray",
        "node",
        ".yaml",
        ".txt",
    ]


    return any(
        x in url
        for x in keys
    )



# ===============================
# 转换订阅
# ===============================

def convert_sub(
        scraper,
        target,
        url
):

    timestamp = int(time.time())


    for api in SUB_APIS:

        try:

            print(
                f"🔄 {api} -> {target}"
            )


            params = {

                "target": target,

                "url": url,

                "insert": "false",

                "_t": timestamp,

            }


            res = request_retry(
                scraper,
                api,
                params=params,
                timeout=30
            )


            if res.status_code != 200:

                continue



            text = res.text.strip()



            if "<html" in text.lower():

                continue



            if target == "clash":

                if (
                    "proxies:" in text
                    and len(text) > 100
                ):

                    return text



            if target == "v2ray":

                if len(text) > 50:

                    return text



        except Exception as e:

            print(
                "转换失败:",
                e
            )



    return None



# ===============================
# 主抓取
# ===============================

def fetch_links():


    print(
        "🌐 请求 yfamilys..."
    )


    scraper = cloudscraper.create_scraper(
        browser={
            "browser":"chrome",
            "platform":"windows",
            "desktop":True
        }
    )


    headers = {

        "User-Agent":
        "Mozilla/5.0 Chrome/120",

        "Accept-Language":
        "zh-CN,zh;q=0.9"

    }



    response = request_retry(

        scraper,

        TARGET_URL,

        headers=headers,

        timeout=30

    )


    response.raise_for_status()



    html_text = html.unescape(
        response.text
    )



    extracted = None



    # 节点

    node_pattern = (

        r"(?:vmess|vless|trojan|ss|ssr|"
        r"hysteria|hysteria2|hy2|tuic)"
        r"://[^\s<\"'>]+"

    )


    nodes = re.findall(
        node_pattern,
        html_text,
        re.I
    )



    if nodes:

        nodes = list(
            dict.fromkeys(nodes)
        )

        extracted = "\n".join(nodes)


        print(
            f"找到 {len(nodes)} 节点"
        )



    else:


        # yfamilys订阅

        pattern = (
            r"https://yfamilys\.com/subscribe/"
            r"[A-Za-z0-9_\-?=&]+"
        )


        result = re.findall(
            pattern,
            html_text
        )


        if result:

            extracted = result[0]

            print(
                "找到订阅:",
                extracted
            )



        else:


            soup = BeautifulSoup(
                html_text,
                "html.parser"
            )


            urls = [

                a["href"]

                for a in soup.find_all(
                    "a",
                    href=True
                )

            ]


            urls += re.findall(
                r"https?://[^\s<\"'>]+",
                html_text
            )


            for u in dict.fromkeys(urls):

                if is_valid_sub_url(u):

                    extracted = u

                    break




    if not extracted:

        raise Exception(
            "没有找到有效订阅"
        )



    print(
        "✅ 提取:",
        extracted[:100]
    )



    now = time.strftime(
        "%Y-%m-%d %H:%M:%S UTC",
        time.gmtime()
    )


    safe_write(
        "links.txt",
        extracted
    )



    # V2Ray

    if extracted.startswith("http"):


        v2ray = convert_sub(
            scraper,
            "v2ray",
            extracted
        )


        if not v2ray:

            raise Exception(
                "V2Ray转换失败"
            )


        safe_write(

            "v2ray.txt",

            f"// Updated: {now}\n"
            + v2ray

        )



    else:


        data = base64.b64encode(
            extracted.encode()
        ).decode()


        safe_write(
            "v2ray.txt",
            data
        )



    print(
        "✅ V2Ray完成"
    )



    # Clash


    clash = convert_sub(
        scraper,
        "clash",
        extracted
    )


    if not clash:

        raise Exception(
            "Clash转换失败"
        )



    safe_write(

        "clash.yaml",

        f"# Updated: {now}\n"
        + clash

    )


    print(
        "✅ Clash完成"
    )



    update_readme(
        extracted
    )



    print(
        "🎉 全部完成"
    )





if __name__ == "__main__":

    fetch_links()
