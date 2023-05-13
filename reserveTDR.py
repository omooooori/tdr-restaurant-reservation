# coding:utf-8
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from time import sleep
import requests, os, datetime, yaml, warnings, calendar

warnings.simplefilter('ignore')
from selenium.webdriver.chrome.options import Options
from pywebio.input import select, checkbox, radio, textarea, file_upload, input_group
from pywebio.output import put_markdown, put_table, put_buttons, put_image, put_text, popup, put_html, close_popup
from datetime import datetime
from datetime import timedelta
from pynotificator import DesktopNotification


# カレンダーの作成
def get_date_list():
    dt_now = datetime.now()
    year = dt_now.year
    month = dt_now.month
    day = dt_now.day
    date_list = [datetime(year, month, day) + timedelta(days=i) for i in range(calendar.monthrange(2019, 1)[1])]
    date_str_list = [d.strftime("%Y/%m/%d") for d in date_list]
    return date_str_list


# レストランのリスト作成
def get_restaurant_name():
    a = open("restaurant.txt", "r")
    restaurant_name = []
    dict_restaurant = {}
    for line in a:
        restaurant_name.append(line.rstrip().rsplit(" ")[1])
        dict_restaurant[line.rstrip().rsplit(" ")[1]] = line.rstrip().rsplit(" ")[0]
    a.close()
    return restaurant_name, dict_restaurant


# 入力フォーム
def input_form(restaurant_list):
    adult_list = list(range(1, 11))
    result = input_group("TDRモニタリング", [
        select('レストラン', restaurant_list, name="restaurant"),
        select('人数', adult_list, name="adult"),
        select('インパ予定日', get_date_list(), name="date"),
        radio("インターバル", options=["1分", "5分", "10分"], inline=True, name="interval"),
    ])
    return result


# 入力エラーの場合のポップアップ
def show_popup():
    popup('入力に不備があります', [
        put_markdown('**インターバル**を選択してください'),
        put_buttons(['Close'], onclick=lambda _: close_popup())
    ])


# モニタリング開始確認
def output(result, dict_restaurant):
    put_html('<h1>以下の内容でモニタリングを開始しました<br>予約空きが見つかればLINEでお知らせします</h1>')
    put_table([
        ["レストラン", result["restaurant"]],
        ["人数", str(result["adult"]) + "人"],
        ["インパ予定日", result["date"]],
        ["インターバル", result["interval"]],
    ])
    # YAMLファイルへ書き込む
    with open("config.yaml", "w") as yf:
        yaml.dump(result, yf, encoding='utf8', allow_unicode=True, default_flow_style=False)


# フォームの入力から実行開始まで
def form():
    while True:
        restaurant_list, dict_restaurant = get_restaurant_name()
        result = input_form(restaurant_list)
        print(result)
        if result["interval"] is None:
            show_popup()
        else:
            break
    output(result, dict_restaurant)
    dn = DesktopNotification('のモニタリングを開始しました', title='TDRモニタリング', subtitle=result["restaurant"])
    dn.notify()


# 設定ファイルの読み込み
def read_config():
    with open('config.yaml', 'r') as yml:
        config = yaml.safe_load(yml)
        print(config)
        return config


# レストランの辞書型を作成
def read_restaurant():
    dict_restaurant = {}
    a = open("restaurant.txt", "r")
    for i in a:
        i = i.rstrip()
        num = i.split(" ")[0]
        name = i.split(" ")[1]
        dict_restaurant[name] = num
    a.close()
    return dict_restaurant


# LINE通知
def send_line_notify(notification_message):
    line_notify_token = '9wgkh5tHAq3ZmfA01rnzj2CuT4bkKEiJVfon2Dlehb9'
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': f'{notification_message}'}
    requests.post(line_notify_api, headers=headers, data=data)


# ブラウザ操作部分
def chrome(config, dict_restaurant):
    # ChromeDriverの起動
    options = Options()
    driver = webdriver.Chrome('./chromedriver')
    driver.implicitly_wait(10)

    try:
        # 予約トップページへ遷移
        driver.get("https://reserve.tokyodisneyresort.jp/top/")
        sleep(3)

        # "レストラン"のイメージリンクをクリック
        driver.find_element_by_xpath("//img[@src='/cgp/images/jp/pc/btn/btn_gn_04.png']").click();
        sleep(3)

        # 同意書の同意ボタンをクリック
        driver.find_element_by_xpath("//img[@src='/cgp/images/jp/pc/btn/btn_close_08.png']").click();
        driver.implicitly_wait(3)

        # 日付の指定
        driver.find_element_by_id('searchUseDateDisp').send_keys(config["date"])

        # 人数の指定
        color_element = driver.find_element_by_id('searchAdultNum')
        color_select_element = Select(color_element)
        color_select_element.select_by_value(str(config["adult"]))

        # レストランの指定
        color_element = driver.find_element_by_id('nameCd')
        color_select_element = Select(color_element)
        color_select_element.select_by_value(dict_restaurant[config["restaurant"]])

        # "検索する"をクリック
        driver.find_element_by_xpath("//input[@src='/cgp/images/jp/pc/btn/btn_search_01.png']").click();
        sleep(1)

        # ページのスクロール
        height = driver.execute_script("return document.body.scrollHeight")
        for x in range(1, height):
            driver.execute_script("window.scrollTo(0, " + str(x) + ");")
        sleep(3)

        # 検索結果から空き状況を判定
        if "お探しの条件で、空きはございません。" in driver.find_element_by_id('hasNotResultDiv').text:
            print(driver.find_element_by_id('hasNotResultDiv').text)
        else:
            print("空きが見つかりました")
            send_line_notify('空きが出ました\n')

        # ChromeDriverを閉じる
        driver.close()

    # メンテナンス中の場合
    except:
        driver.close()
        print("只今メンテナンス中です")


form()  # 入力フォーム
while True:
    config = read_config()  # 設定ファイルの読み込み
    dict_restaurant = read_restaurant()  # レストランの辞書作成
    chrome(config, dict_restaurant)  # ブラウザの操作
    sleep(int(config["interval"].replace("分", "")) * 60)  # 一定時間スリープ
