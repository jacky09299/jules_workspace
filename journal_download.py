import feedparser
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import json
import os
import time
import random
import string
import re
from urllib.parse import urlparse
from datetime import datetime

def generate_random_filename(prefix='config_', suffix='.json', length=6):
    """產生亂碼設定檔名"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}{random_str}{suffix}"

def clean_text(text):
    """Remove HTML tags and clean the text."""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text().strip()

def convert_science_url_to_pdf(article_url):
    """將 Science 網頁版網址轉換為 PDF 版網址"""
    base_url = article_url.split('?')[0]
    pdf_url = base_url.replace('/doi/abs/', '/doi/pdf/') + '?download=true'
    return pdf_url

def fetch_science_articles():
    """Fetch the latest articles from Science journal."""
    print("擷取 Science 期刊文章...")
    try:
        feed = feedparser.parse('https://www.science.org/action/showFeed?type=axatoc&feed=rss&jc=science')
        articles = []
        for entry in feed.entries:
            published_date = getattr(entry, 'published', getattr(entry, 'updated', "Date not available"))
            original_link = getattr(entry, 'link', "#")
            pdf_link = convert_science_url_to_pdf(original_link) if original_link != "#" else "#"
            article = {
                'title': getattr(entry, 'title', "No title available"),
                'link': pdf_link,
                'published': published_date,
                'summary': clean_text(getattr(entry, 'summary', "No summary available")),
                'source': 'Science'
            }
            articles.append(article)
        print(f"✅ 成功擷取 {len(articles)} 篇 Science 文章 (已轉換為PDF版網址)")
        return articles
    except Exception as e:
        print(f"❌ Science 擷取失敗：{e}")
        return []

def fetch_nature_articles():
    """Fetch the latest articles from Nature journal."""
    print("擷取 Nature 期刊文章...")
    try:
        feed = feedparser.parse('https://www.nature.com/nature.rss')
        articles = []
        for entry in feed.entries:
            published_date = getattr(entry, 'published', getattr(entry, 'updated', "Date not available"))
            article = {
                'title': getattr(entry, 'title', "No title available"),
                'link': getattr(entry, 'link', "#"),
                'published': published_date,
                'summary': clean_text(getattr(entry, 'summary', "No summary available")),
                'source': 'Nature'
            }
            articles.append(article)
        print(f"✅ 成功擷取 {len(articles)} 篇 Nature 文章")
        return articles
    except Exception as e:
        print(f"❌ Nature 擷取失敗：{e}")
        return []

def fetch_aps_articles():
    """Fetch the latest articles from APS Physics Review journals."""
    print("擷取 APS Physics Review 文章...")
    try:
        feed = feedparser.parse('https://feeds.aps.org/rss/allsuggestions.xml')
        articles = []
        for entry in feed.entries:
            published_date = getattr(entry, 'published', getattr(entry, 'updated', "Date not available"))
            article = {
                'title': getattr(entry, 'title', "No title available"),
                'link': getattr(entry, 'link', "#"),
                'published': published_date,
                'summary': clean_text(getattr(entry, 'summary', "No summary available")),
                'source': 'APS'
            }
            articles.append(article)
        print(f"✅ 成功擷取 {len(articles)} 篇 APS 文章")
        return articles
    except Exception as e:
        print(f"❌ APS 擷取失敗：{e}")
        return []

def fetch_economist_articles():
    """Fetch the latest articles from The Economist journal."""
    print("擷取 The Economist 文章...")
    try:
        feed = feedparser.parse('https://www.economist.com/the-world-this-week/rss.xml')
        articles = []
        for entry in feed.entries:
            published_date = getattr(entry, 'published', getattr(entry, 'updated', "Date not available"))
            article = {
                'title': getattr(entry, 'title', "No title available"),
                'link': getattr(entry, 'link', "#"),
                'published': published_date,
                'summary': clean_text(getattr(entry, 'summary', "No summary available")),
                'source': 'The Economist'
            }
            articles.append(article)
        print(f"✅ 成功擷取 {len(articles)} 篇 The Economist 文章")
        return articles
    except Exception as e:
        print(f"❌ The Economist 擷取失敗：{e}")
        return []

def fetch_pbs_articles():
    """Fetch the latest articles from PBS NewsHour."""
    print("擷取 PBS NewsHour 文章...")
    try:
        feed = feedparser.parse('https://www.pbs.org/newshour/feeds/rss/headlines')
        articles = []
        for entry in feed.entries:
            published_date = getattr(entry, 'published', getattr(entry, 'updated', "Date not available"))
            article = {
                'title': getattr(entry, 'title', "No title available"),
                'link': getattr(entry, 'link', "#"),
                'published': published_date,
                'summary': clean_text(getattr(entry, 'summary', "No summary available")),
                'source': 'PBS NewsHour'
            }
            articles.append(article)
        print(f"✅ 成功擷取 {len(articles)} 篇 PBS NewsHour 文章")
        return articles
    except Exception as e:
        print(f"❌ PBS NewsHour 擷取失敗：{e}")
        return []

def fetch_all_articles():
    """擷取所有來源的文章網址與資訊"""
    print("開始擷取所有期刊文章...")
    all_articles = []
    
    # 依序抓取各期刊內容
    all_articles.extend(fetch_science_articles())
    all_articles.extend(fetch_nature_articles())
    all_articles.extend(fetch_aps_articles())
    all_articles.extend(fetch_economist_articles())
    all_articles.extend(fetch_pbs_articles())

    # 使用字典來去重，保留第一次出現的文章
    unique_articles_dict = {article['link']: article for article in reversed(all_articles) if article['link'] != "#"}
    unique_articles = list(reversed(list(unique_articles_dict.values())))

    print(f"\n📋 總共擷取到 {len(unique_articles)} 篇不重複的文章")
    for i, article in enumerate(unique_articles[:10], 1):
        print(f"  {i}. [{article['source']}] {article['link']}")

    if len(unique_articles) > 10:
        print(f"  ... 還有 {len(unique_articles) - 10} 篇文章")

    return unique_articles

def create_config_file(target_urls):
    """建立亂碼設定檔並回傳檔名"""
    filename = generate_random_filename()
    config = {
        # 注意: 此路徑為基礎路徑，實際儲存時會在此路徑下建立時間戳資料夾
        "base_download_path": "C:\\Users\\User\\Downloads\\Journal_papers",
        "chromedriver_path": "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chromedriver.exe",
        "target_urls": target_urls, # 雖然URL在處理時會從article物件讀取，但保留此項以便快速預覽
        "implicit_wait_time": 10,
        "print_settings": {
            "selectedDestinationId": "Save as PDF",
            "version": 2
        },
        "chrome_options": [
            "--kiosk-printing",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor"
        ]
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

    print(f"✅ 已建立設定檔：{filename}")
    return filename

def load_config(config_file):
    """載入指定設定檔"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_chrome_options(config, save_path):
    """設定 Chrome 選項，並指定動態儲存路徑"""
    chrome_options = webdriver.ChromeOptions()
    app_state = {
        'recentDestinations': [{'id': 'Save as PDF', 'origin': 'local', 'account': ''}],
        'selectedDestinationId': config['print_settings']['selectedDestinationId'],
        'version': config['print_settings']['version']
    }
    # 為本次下載/列印設定指定的儲存路徑
    prefs = {
        'printing.print_preview_sticky_settings.appState': json.dumps(app_state),
        'savefile.default_directory': save_path,
        "download.default_directory": save_path,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_argument("--window-size=10,10")
    chrome_options.add_argument("--window-position=0,0")
    #chrome_options.add_argument("--window-position=100000,100000")
    for option in config['chrome_options']:
        chrome_options.add_argument(option)
    return chrome_options

def download_nature_pdf(url, save_path):
    """偵測Nature文章，直接下載PDF到指定路徑"""
    try:
        article_id = os.path.basename(urlparse(url).path)
        if not article_id:
            print(f"❌ 無法從 Nature URL 中解析文章 ID: {url}")
            return

        pdf_url = f"https://www.nature.com/articles/{article_id}.pdf"
        # 使用文章ID作為檔名，並確保是有效的檔案名稱
        safe_filename = re.sub(r'[\\/*?:"<>|]', "", article_id)
        filename = os.path.join(save_path, f"{safe_filename}.pdf")

        print(f"📄 準備從 {pdf_url} 下載")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ Nature PDF 已成功儲存至: {filename}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Nature PDF 下載失敗: {e}")
    except Exception as e:
        print(f"❌ 處理 Nature PDF 時發生未知錯誤: {e}")

def convert_aps_url(short_url):
    """追蹤APS短網址，解析最終網址來建立PDF連結"""
    print(f"  ➡️ 正在解析 APS 短網址: {short_url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(short_url, headers=headers, allow_redirects=True, timeout=20)
        final_url = response.url
        print(f"  ➡️ 已解析得到最終網址: {final_url}")

        match = re.search(r'journals.aps.org/([a-z]+)/.*/(10\.1103/.+)', final_url)
        if match:
            journal_code = match.group(1)
            full_doi = match.group(2).split('?')[0]
            pdf_url = f"https://journals.aps.org/{journal_code}/pdf/{full_doi}"
            return pdf_url
        else:
            print(f"  ❌ 無法從最終網址中解析所需資訊: {final_url}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"  ❌ 解析 APS 短網址時發生網路錯誤: {e}")
        return None
    except Exception as e:
        print(f"  ❌ 解析 APS 短網址時發生未知錯誤: {e}")
        return None
        
def clean_temp_downloads(download_path):
    """刪除指定下載資料夾中的 .crdownload 和 .tmp 檔案"""
    for filename in os.listdir(download_path):
        if filename.endswith('.crdownload') or filename.endswith('.tmp'):
            file_path = os.path.join(download_path, filename)
            try:
                os.remove(file_path)
                print(f"🗑️ 已刪除暫存檔案: {filename}")
            except Exception as e:
                print(f"⚠️ 無法刪除 {filename}: {e}")

def wait_for_downloads_to_finish(download_path, check_interval=1):
    """等待直到指定下載資料夾中沒有 .crdownload 或 .tmp 檔案"""
    print(f"⏳ 等待檔案在 [{os.path.basename(download_path)}] 資料夾中儲存完成...")
    while any(f.endswith((".crdownload", ".tmp")) for f in os.listdir(download_path)):
        time.sleep(check_interval)
    print("📁 所有檔案已處理完成")

def process_urls(config, articles_to_process, execution_path):
    """處理多個網址，根據來源下載或列印到對應的期刊資料夾"""
    if not os.path.exists(config['chromedriver_path']):
        print(f"❌ 錯誤：找不到 chromedriver：{config['chromedriver_path']}")
        return

    service = Service(config['chromedriver_path'])
    print(f"\n🚀 開始處理 {len(articles_to_process)} 篇文章...")

    for idx, article in enumerate(articles_to_process, start=1):
        driver = None
        url = article['link']
        source = article.get('source', 'Unknown_Journal') # 取得來源，若無則設為未知
        
        # 1. 建立該期刊專屬的儲存資料夾
        journal_save_path = os.path.join(execution_path, source)
        os.makedirs(journal_save_path, exist_ok=True)
        
        print(f"\n[{idx}/{len(articles_to_process)}] 正在處理: {url}")
        print(f"  ➡️ 來源: {source} | 儲存至: {journal_save_path}")

        try:
            if 'nature.com' in url:
                print("➡️ 偵測到 Nature 期刊，執行直接下載...")
                download_nature_pdf(url, journal_save_path)
                time.sleep(2)

            elif 'science.org' in url and '/pdf/' in url:
                print("➡️ 偵測到 Science 期刊，使用瀏覽器直接下載...")
                chrome_options = setup_chrome_options(config, journal_save_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.implicitly_wait(config['implicit_wait_time'])
                clean_temp_downloads(journal_save_path)
                print("  正在啟動下載...")
                driver.get(url)
                wait_for_downloads_to_finish(journal_save_path)
                print(f"✅ 下載結束: {url}")
                
            else: # 通用列印法 (適用於 APS, PBS, The Economist 等)
                print(f"➡️ 偵測到通用網址，使用列印法儲存...")
                process_url = url
                if 'aps.org' in url:
                    print("  ➡️ APS 期刊，需先轉換URL...")
                    process_url = convert_aps_url(url)
                    if process_url is None:
                        print("  APS URL 轉換失敗，跳過此網址。")
                        continue
                    print(f"  🔄 準備使用轉換後的PDF網址列印: {process_url}")

                chrome_options = setup_chrome_options(config, journal_save_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.implicitly_wait(config['implicit_wait_time'])
                driver.get(process_url)
                time.sleep(10)  # 等待頁面載入，特別是APS的PDF檢視器

                print("🖨️  執行列印...")
                driver.execute_script('window.print();')
                wait_for_downloads_to_finish(journal_save_path)
                print(f"✅ 列印/儲存成功: {process_url}")

        except Exception as e:
            print(f"❌ 處理 {url} 時發生錯誤: {e}")
        finally:
            if driver:
                driver.quit()
                print("🚪 瀏覽器已關閉")
            time.sleep(random.uniform(1, 3))

def save_articles_info(articles, save_path):
    """儲存文章資訊到指定路徑的文字檔"""
    filename = os.path.join(save_path, "articles_summary.txt")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"期刊文章資訊 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        articles_by_source = {}
        for article in articles:
            source = article.get('source', 'N/A')
            if source not in articles_by_source: articles_by_source[source] = []
            articles_by_source[source].append(article)
        
        for source, arts in articles_by_source.items():
            f.write(f"--- {source} ({len(arts)} 篇) ---\n\n")
            for i, article in enumerate(arts, 1):
                f.write(f"[{i}] 標題: {article['title']}\n")
                f.write(f"    發布日期: {article['published']}\n")
                f.write(f"    連結: {article['link']}\n")
                f.write(f"    摘要: {article['summary'][:200]}...\n")
                f.write("-" * 60 + "\n")
            f.write("\n")

    print(f"📄 已儲存文章摘要資訊到：{filename}")

def main():
    print("🔄 期刊文章擷取與處理系統 v3.0 (自動分類儲存)")
    print("=" * 50)
    
    # --- 建立本次執行的主資料夾 ---
    base_download_path = "C:\\Users\\User\\Downloads\\Journal_papers"
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    execution_path = os.path.join(base_download_path, timestamp)
    
    try:
        os.makedirs(execution_path, exist_ok=True)
        print(f"📁 已建立本次執行主資料夾：{execution_path}")
    except OSError as e:
        print(f"❌ 建立主資料夾失敗: {e}\n程式即將結束。")
        return
    # -----------------------------

    articles = fetch_all_articles()

    if not articles:
        print("❌ 沒有擷取到任何文章，程式結束。")
        return

    save_articles_info(articles, execution_path)

    print(f"\n📋 總共擷取到 {len(articles)} 篇文章")
    choice = input("是否要開始處理 (下載/列印)？(y/n): ").lower().strip()

    if choice == 'y':
        articles_to_process = articles
        limit_str = input(f"要處理全部 {len(articles)} 篇文章嗎？(輸入數字限制數量，或按 Enter 處理全部): ").strip()

        if limit_str.isdigit() and int(limit_str) > 0:
            limit = int(limit_str)
            articles_to_process = articles[:limit]
            print(f"⚠️ 已限制處理前 {len(articles_to_process)} 篇文章")
        
        # 從要處理的文章列表中提取URL來建立設定檔
        urls_to_process = [article['link'] for article in articles_to_process]
        config_file = create_config_file(urls_to_process)
        config = load_config(config_file)
        
        # 傳入設定、要處理的文章列表、以及本次執行的主路徑
        process_urls(config, articles_to_process, execution_path)

        try:
            os.remove(config_file)
            print(f"\n🧹 已成功刪除暫存設定檔：{config_file}")
        except Exception as e:
            print(f"\n⚠️ 無法刪除暫存設定檔：{e}")
    else:
        print("🟢 已取消處理，僅完成文章擷取與資訊保存。")

if __name__ == "__main__":
    main()