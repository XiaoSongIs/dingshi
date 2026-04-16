import requests
import os
import schedule
import time
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from datetime import datetime

#每天的执行时间
time_str = "21:37"  

# 企业微信机器人 Webhook Key
WEBHOOK_KEY = "9ada6f34-5ab3-4b5c-af73-e5d56573ffba"

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#合并路径
PDF_DIR = os.path.join(BASE_DIR, "pdf")
os.makedirs(PDF_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0"
}
 
# 获取pdf所有的下载连接
index = range(1,8)

def get_pdf_urls(i):
    today = datetime.now()
    date_str = today.strftime("%Y%m/%d")

    url = f"http://paper.people.com.cn/rmrb/pc/layout/{date_str}/node_0{i}.html"
    res = requests.get(url, headers=headers)
    
    res.encoding = 'utf-8'

    soup = BeautifulSoup(res.text, 'html.parser')

    pdf_urls = []

    # 找所有 a 标签
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "attachement" in href:
            path = href.split("attachement")[-1]
            full_url = "http://paper.people.com.cn/rmrb/pc/attachement" + path
            pdf_urls.append(full_url)

    return pdf_urls



def download_pdfs(pdf_urls):
    for i, pdf_url in enumerate(pdf_urls):
        res = requests.get(pdf_url, headers=headers)
        file_name = f"{datetime.now().strftime('%Y-%m-%d')}人民日报_{i+1}.pdf"
        file_path = os.path.join(BASE_DIR, file_name)
        
        with open(file_path, "wb") as f:
            f.write(res.content)
        print(f"已下载: {file_name}")
        
    return file_path

def upload_file(file_path):
    upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={WEBHOOK_KEY}&type=file"

    files = {
        'file': open(file_path, 'rb')
    }

    res = requests.post(upload_url, files=files)

    result = res.json()
    print("上传结果:", result)

    return result.get("media_id")


# 发送文件
def send_file(media_id):
    send_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}"

    data = {
        "msgtype": "file",
        "file": {
            "media_id": media_id
        }
    }

    res = requests.post(send_url, json=data)

    print("发送结果:", res.json())


# def job():
#     print("开始流程...")
#     for i in range(3):
#         print(f"第{i+1}次尝试...")
#         for j in index:
#             pdf_url = get_pdf_urls(j)    
#             if pdf_url:
#                 file_path = download_pdfs(pdf_url)
#                 media_id = upload_file(file_path)
#                 send_file(media_id)
#                 print("发送成功")
#                 return
#             time.sleep(600)  # 等10分钟再试
#     print("今日获取失败")

def job():
    print("开始流程...")
    all_pdf_urls = []
    # 收集所有版面PDF
    for j in index:
        pdf_urls = get_pdf_urls(j)
        if pdf_urls:
            all_pdf_urls.extend(pdf_urls)
        else:
            print(f"第{j}版未获取到")
    if not all_pdf_urls:
        print("没获取到任何PDF")
        return
    print(f"共获取到 {len(all_pdf_urls)} 个PDF")
    # 下载全部
    file_paths = download_all_pdfs(all_pdf_urls)
    # 合并
    merged_file = merge_pdfs(file_paths)
    # 上传+发送
    media_id = upload_file(merged_file)
    if not media_id:
        print("上传失败")
        return
    send_file(media_id)
    print("今日人民日报已发送（合集版）")


# 下载所有PDF文件
def download_all_pdfs(pdf_urls):
    file_paths = []

    for i, pdf_url in enumerate(pdf_urls, 1):
        file_name = f"page_{i}.pdf"
        file_path = os.path.join(PDF_DIR, file_name)

        res = requests.get(pdf_url)

        with open(file_path, "wb") as f:
            f.write(res.content)

        print(f"已下载: {file_name}")
        file_paths.append(file_path)

    return file_paths

# 合并PDF文件
def merge_pdfs(file_paths):
    merger = PdfMerger()

    for path in file_paths:
        merger.append(path)

    merged_path = os.path.join(BASE_DIR, f"{datetime.now().strftime('%Y-%m-%d')}人民日报合集.pdf")

    merger.write(merged_path)
    merger.close()
    clear_temp_pdfs()
    print("合并完成:", merged_path)

    return merged_path

# 清理临时PDF文件
def clear_temp_pdfs():
    for f in os.listdir(PDF_DIR):
        file_path = os.path.join(PDF_DIR, f)
        if f.endswith(".pdf"):
            os.remove(file_path)
    print("已清理临时PDF")

if __name__ == "__main__":
    # 每天执行
    schedule.every().day.at(time_str).do(job)
    print("定时任务已启动...")
    while True:
        schedule.run_pending()
        time.sleep(60)
   
