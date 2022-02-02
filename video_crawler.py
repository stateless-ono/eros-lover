import os
import requests
import time
import re
import pandas as pd
from bs4 import BeautifulSoup as bs
import datetime
import schedule
# CSVのパスは複数のファイルで使用するのでconfig.pyに記述して、読み込む
from config import VIDEO_CSV_PATH
# 本日の日付を文字列化(指定のフォーマットを適用)
today = datetime.datetime.today().strftime("%Y-%m-%d")
def parse_video_id(url: str):
    '''
    URLからvideo_idを切り出す
    '''
    m = re.search(r"\/player\/([0-9]*)\/", url)    
    if m:
        return m.group(1)
    else:
        return None
def fetch_video_detail(url: str):
    '''
    URLからvideo詳細情報を取得
    '''
    res = requests.get(url)
    res.raise_for_status()
    soup = bs(res.text, "html.parser")
    # タイトルを取得
    title = soup.select_one("article h1").text
    # VideoのオリジナルＵＲＬを取得
    video_url = soup.select_one("iframe").get("src")
    # タグ情報を取得
    tag_elms = soup.select("ul.tag_list > li")
    tags = []
    for tag_elm in tag_elms:
        tags.append(tag_elm.text)
    video_id = parse_video_id(str(video_url))
    # video_idが取得出来ない場合はNone(データなし)を返す
    if not video_id:
        return None
    video = {
        "title": title,
        "video_url": "https:" + str(video_url), # URLにhttpsが含まれていないので追加する
        "tags": tags,
        "video_id": video_id,
        "thumbnail_url": f"https://img.javynow.com/files/{video_id[-1]}/{video_id}.jpg" # サムネイルURLを作成(JavyNowのページからURLの法則を解析した)
    }
    return video
def export_csv(videos: list):
    '''
    ＣＳＶ出力処理(追記)
    pandas(pd)ライブラリを使用すると簡単にCSV出力が可能
    '''
    # 既にファイルが存在する場合は取得済の情報を一旦インポート
    # DataFrame形式のデータの入れ物を定義する(pandasの仕様)
    if os.path.exists(VIDEO_CSV_PATH):
        df = pd.read_csv(VIDEO_CSV_PATH)
    else:
        df = pd.DataFrame()    
    # CSV出力用のデータを作成
    for i, video in enumerate(videos):
        # データを追加
        df = df.append({
            "post_id": "",
            "post_name": "",
            "post_author": "",
            "post_date": f"{today}-{i+1}" ,
            "post_type": "post", # 投稿
            "post_status": "publish", # 公開
            "post_title": video.get("title"),
            "post_content": f'<iframe src="{video.get("video_url")}" frameborder="0" width="560" height="315" scrolling="no" allowfullscreen></iframe>', # 文字列に"(ダブルクォーテーション)が含まれる場合は両端は'(シングルクォーテーション)を使用する
            "post_category": "",
            "post_tags": ",".join(video.get("tags")),
            "menu_order": "",
            "post_thumbnail": video.get("thumbnail_url")
        }, ignore_index=True)
    # CSV出力
    df = df[~df.duplicated(subset="post_title")] # 重複するURLは削除
    df.to_csv(VIDEO_CSV_PATH)
def crawle(start_page: int=1, end_page: int=5):
    '''
    メイン処理（クロール）
    全件のURLを指定して、取得する
    '''
    # 一覧ページから動画詳細ページへのリンクを取得する
    # ページ番号を指定することで複数ページ分を繰り返し取得する
    detail_links = []
    for page in range(start_page, end_page+1):
        try:
            print(f"list page crawring | page={page}")
            # URLの?以降の部分を以下のparamsのように指定し、requests.getのparamsに渡すと以下のようなURLに変換してくれる
            # https://erry.one/all/?s=JavyNow&p=2
            params = {
                "s": "JavyNow", # サイトをフィルター
                "p": page # ページ番号
            }
            res = requests.get("https://erry.one/all/", params=params)
            res.raise_for_status()
            soup = bs(res.text, "html.parser")
            detail_elms = soup.select("article h2 a")
            for detail_elm in detail_elms:
                detail_links.append(detail_elm.get("href"))
        except Exception as e:
            print(e)
    print(f"detail url count={len(detail_links)}")
    # 詳細ページを参照して動画情報を取得する
    videos = []
    for detail_link in detail_links:
        try:
            print(detail_link)
            video = fetch_video_detail(f"https://erry.one/{detail_link}")
            print(video)
            videos.append(video)
        except Exception as e:
            print(f"fetch detail page failed | detail={e}")
    # CSVを出力する
    export_csv(videos)
def set_schedule():
    # １分に１回実行
    schedule.every(6).hours.do(crawle, 1, 5)
if __name__ == "__main__":
    # スケジュールをセット
    set_schedule()
    while True:
        schedule.run_pending()
        print("pending...")
        time.sleep(60)