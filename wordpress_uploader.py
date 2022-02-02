import os
from subprocess import check_output
import time
import math
import schedule
import pandas as pd
import pathlib
import glob
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service
from webdriver_manager.chrome import ChromeDriverManager
# CSVのパスは複数のファイルで使用するのでconfig.pyに記述して、読み込む
from config import VIDEO_CSV_PATH
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
WORDPRESS_LOGIN_URL = "https://eros-lover.com/wp-admin/"
WORDPRESS_CSV_IMPORT_URL = "https://eros-lover.com/wp-admin/admin.php?import=csv"
WORDPRESS_ARTICLES_URL = "https://eros-lover.com/wp-admin/edit.php"
UPLOAD_CSV_PATH = "csv/temp_upload_{index}.csv"
LOGIN_ID = "smallbroom21"
PASSWORD = r"C&%sgKP82V" # 先頭のrは%などの特殊文字列を無視して、文字列として扱ういう意味
def start_chrome():
    '''
    ChromeDriverを起動してブラウザを開始する
    '''
    # Chromeドライバーの読み込み
    options = ChromeOptions()
    options.add_argument('--user-agent=' + USER_AGENT) #　リクエストヘッダ
    options.add_argument('log-level=3')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    # ChromeのWebDriverオブジェクトを作成する。
    try:
        driver = Chrome(service=service.Service(ChromeDriverManager().install()),
                        options=options)
        return driver
    except Exception as e:
        raise Exception(f"driver起動エラー:{e}")
def login(chrome: Chrome):
    # ログイン
    chrome.get(WORDPRESS_LOGIN_URL)
    time.sleep(1)
    chrome.find_element(by=By.ID, value="user_login").send_keys(LOGIN_ID)
    time.sleep(1)
    chrome.find_element(by=By.ID, value="user_pass").send_keys(PASSWORD)
    time.sleep(1)
    chrome.find_element(by=By.ID, value="wp-submit").click()
    time.sleep(1)
def fetch_article_titles(chrome: Chrome, page_limit: int=None):
    '''
    投稿済の記事タイトルを取得
    '''
    chrome.get(WORDPRESS_ARTICLES_URL)
    total_pages_text = chrome.find_element(by=By.CSS_SELECTOR, value=".total-pages").text
    if not total_pages_text:
        total_pages = 1
    else:
        total_pages = int(total_pages_text)
    fetch_page_limit = total_pages
    if page_limit and total_pages > page_limit:
        fetch_page_limit = page_limit
    print(f"fetch_page_limit={fetch_page_limit}, total_pages={total_pages}, page_limit={page_limit}")
    titles = []
    for page in range(fetch_page_limit):
        print(f"page={page+1}")
        chrome.get(f"{WORDPRESS_ARTICLES_URL}?paged={page+1}")
        time.sleep(1)
        title_elms = chrome.find_elements(by=By.CSS_SELECTOR, value=".row-title")
        for title_elm in title_elms:
            titles.append(title_elm.text)
    return titles
def make_filtered_post_items_csv(current_posted_titles: list, onetime_post_limit: int=10):
    '''
    大量のデータをUploadするとタイムアウトするので、ファイルを分割して複数回に分ける
    (デフォルトでは、１ファイルあたり最大１０アイテムとする)
    '''
    df = pd.read_csv(VIDEO_CSV_PATH)
    post_df = df[~df["post_title"].isin(current_posted_titles)]
    # 前回使ったファイルを削除
    for filepath in glob.glob(UPLOAD_CSV_PATH.format(index="*")):
        if os.path.isfile(filepath):
            os.remove(filepath)
    #sliced_post_dfs = []
    for i in range(int(math.ceil(len(post_df)/onetime_post_limit))):
        post_df[i*onetime_post_limit:(i+1)*onetime_post_limit].to_csv(UPLOAD_CSV_PATH.format(index=i+1), encoding="utf-8")
    #post_df.to_csv(UPLOAD_CSV_PATH, encoding="utf-8")
    return post_df
def upload(chrome: Chrome, upload_csv_path: str):
    index = 1
    while True:
        try:
            if not os.path.exists(upload_csv_path.format(index=index)):
                print("ファイル終了")
                break
            # CSVインポートページに移動
            chrome.get(WORDPRESS_CSV_IMPORT_URL)
            time.sleep(1)
            # CSVファイルのPATHを絶対パスに変換
            csv_full_path = str(pathlib.Path(upload_csv_path.format(index=index)).resolve())
            print(f"upload filepath: {csv_full_path}")
            # ファイルを選択
            chrome.find_element(by=By.ID, value="upload").send_keys(csv_full_path)
            time.sleep(1)
            # Upload
            chrome.find_element(by=By.ID, value="submit").click()
            time.sleep(3)
            # 完了を確認
            # "すべて完了しました"の文字列が表示されれば成功
            is_success = False
            elms = chrome.find_elements(by=By.CSS_SELECTOR, value="#wpbody-content h3")
            for elm in elms:
                if elm.text == "すべて完了しました。":
                    is_success = True
            if is_success:
                print(f"Uploadが成功しました | index={index}")
            else:
                print(f"Uploadが失敗しました | index={index}")
            index += 1
        except Exception as e:
            print(f"upload failed | index={index}")
            print(e)
def main():
    chrome = start_chrome()
    login(chrome)
    titles = fetch_article_titles(chrome)
    post_df = make_filtered_post_items_csv(titles)
    if len(post_df) == 0:
        print("アップロード対象件数が０件のため終了します")
        return None
    res =  upload(chrome, UPLOAD_CSV_PATH)
def set_schedule():
    # １分に１回実行
    schedule.every(6).hours.do(main)
if __name__ == "__main__":
    # スケジュールをセット
    set_schedule()
    while True:
        schedule.run_pending()
        print("pending...")
        time.sleep(60)