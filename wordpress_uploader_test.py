from wordpress_uploader import *

'''
テスト実行用のファイル

テスト実行コマンド
・全テスト
　python -m pytest wordpress_uploader_test.py -s
・指定した関数のみの例
　python -m pytest wordpress_uploader_test.py::test_upload -s
'''

def test_upload():
    res = upload("csv/csv_file.csv")
    assert res
    

def test_fetch_article_titles():
    chrome = start_chrome()
    login(chrome)
    res = fetch_article_titles(chrome)
    
    print(res)
    
    assert len(res) >= 1
    

def test_make_filtered_items_csv():
    chrome = start_chrome()
    login(chrome)
    titles = fetch_article_titles(chrome)
    res = make_filtered_post_items_csv(titles)
    print(res)