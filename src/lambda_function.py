from component import *
import gspread
from gspread.utils import rowcol_to_a1
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from selenium.webdriver.chrome.service import Service
import requests
import re
from datetime import datetime
import csv
from util.chatwork import Chatwork
import json
import boto3
from util.chatwork_util import Chatwork_Util

def lambda_handler(event, context):
    if 'win' not in sys.platform:
        print(json.dumps(event, indent=4))
        sheet_data = event['body']
        sheet_data = json.loads(sheet_data)
        spreadsheet_id = sheet_data['sheetId']
        company_name = sheet_data['companyName']
    else:
        spreadsheet_id = event['sheetId']
        company_name = event['companyName']

    mastersheet_id = "1813MXeKilK4IPKrS6xleElMVA2Tt1r3-QiMcelqxB58"
    login_url = "https://part.shufu-job.jp/console/login"
    upload_url = "https://part.shufu-job.jp/console/c_orders/upload"
    download_url = "https://part.shufu-job.jp/console/c_orders/search"

    # s3クライアントの作成
    s3 = boto3.client('s3')

    # chatworkのエラー通知先設定の呼び出し
    room_id = "356389186"
    operator = "[To:7680302]迫田 彬さん"
    messages = []

    # 処理をスタートしたことをchatworkに通知
    messages.append(f'転記開始\n案件名：{company_name}')
    chatwork = Chatwork(room_id, messages, operator)
    chatwork.send_alert_for_chatwork()

    # account_id, account_psの初期値を決める
    account_id = ""
    account_ps = ""

    # driverの初期値を決める
    driver = ""

    # input_file_pathの初期値を決める
    input_file_path = ""

    # error_messagesの初期値を決める
    error_messages = ""

    # error_column_indexの初期値を決める
    error_column_index = ""

    # num_rowsの初期値を決める
    num_rows = ""

    # tmpファイルにあるデータをすべて削除
    if 'win' not in sys.platform:
        clear_tmp_directory()

    # （あなたのサービスアカウント用）Google APIに接続
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('service.json', scope)
    client = gspread.authorize(creds)

    # マスターシートから情報を取得（ログイン情報）
    try:
        # mastersheetからアイパスを取得
        account_id, account_ps, operator = get_account_data(mastersheet_id, company_name)
        print(account_id, account_ps, operator)
    except Exception as e:
        message = f"マスターシートからの情報の取得に失敗しました.\n{str(e)}\n案件名：{company_name}"
        messages.append(message)
        chatwork = Chatwork(room_id, messages, operator)
        chatwork.send_alert_for_chatwork()

    # Open the Spreadsheet with the ID
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.worksheet(company_name)

    # ワークシートのデータを取り出す
    data = sheet.get_all_values()

    # データを DataFrame に転送
    df = pd.DataFrame(data[1:], columns=data[0])  # Assuming first row is column names
    print(df)

    # "転記ステータス"列で値が"済"でない行を抽出
    df = df[df['転記ステータス'] == '']
    print(df)

    if df.empty:
        message = f"転記ステータスが空の求人がありません\n案件名：{company_name}"
        messages.append(message)
        print(messages)
        chatwork = Chatwork(room_id, messages, operator)
        chatwork.send_alert_for_chatwork()
        return

    # spreadsheetから情報を取得してcsvの形に変更
    try:
        # A～CQ列を選択（列名で指定）
        columns = list(df.columns)[:103]  # Adjust the number as needed
        df = df[columns]
        csv_file_name = company_name + ".csv"
        # Check if the script is running on AWS Lambda
        if 'win' not in sys.platform:
            input_file_path = f"/tmp/{csv_file_name}"
        else:
            input_file_path = f"C:/Users/kinoshita-t/Downloads/{csv_file_name}"
        # input_file_path = f"C:/Users/kinoshita-t/Downloads/{csv_file_name}"
        # input_file_path = os.path.join("C:", "Users", "kinoshita-t", "Downloads", csv_file_name).replace('\ ', '/')

        # dfからCP932で変換できない文字を空に変換
        df = df.replace('\u25b7', '', regex=True) #▷
        df = df.replace('\u25b6', '', regex=True) #▶
        df = df.replace('\u2047', '', regex=True) #⁇
        df = df.replace('\u2730', '', regex=True) #✰
        df = df.replace('\u0f1a', '', regex=True) #。

        # DataFrame を CSV ファイルに出力
        df.to_csv(input_file_path, sep=',', encoding='CP932', index=False)
    except Exception as e:
        message = f"スプレッドシートからの情報の取得に失敗しました.\n{str(e)}\n案件名：{company_name}"
        messages.append(message)
        chatwork = Chatwork(room_id, messages, operator)
        chatwork.send_alert_for_chatwork()

    # CSVにしたファイルをしゅふジョブにアップロード
    try:
        chrome_options = Options()
        driver = get_driver(chrome_options)
        # ログイン
        login(driver, account_id, account_ps, login_url)

        # ファイルをアップロード
        df = pd.DataFrame(data[1:], columns=data[0])
        error_messages = upload_csv_file(driver, upload_url, input_file_path)
        num_rows = sheet.row_count  # 現在の行数を取得する
        error_column_index = df.columns.to_list().index('エラー内容')
    except Exception as e:
        message = f"求人情報のアップロードに失敗しました.\n{str(e)}\n案件名：{company_name}"
        messages.append(message)
        chatwork = Chatwork(room_id, messages, operator)
        chatwork.send_alert_for_chatwork()
        error_messages = "ファイルのアップロードに失敗しました"

   # error_messagesにメッセージが格納されている場合は以下の処理を走らせる
    if error_messages:
        try:
            #エラー内容をスプレッドシートに反映
            print(error_messages)
            error_row_index = 2
            range_start = rowcol_to_a1(2, error_column_index + 1)  # convert into A1 notation
            range_end = rowcol_to_a1(num_rows + 1, error_column_index + 1)
            cell_range = f'{sheet.title}!{range_start}:{range_end}'  # Add 'Worksheet' name into A1 notation

            sheet.spreadsheet.values_update(  # Call 'values_update' in the Spreadsheet instance
                cell_range,
                params={'valueInputOption': 'RAW'},
                body={'values': [[""]] * num_rows}
            )
            # write new error message into the specific cell
            error_messages_str = error_messages[1]  # Assuming that error_messages contains only one item
            print(error_messages_str)
            error_messages_lines = error_messages_str.split("\n")
            error_messages_str_single_cell = "\n".join(error_messages_lines)
            cell_range_error = f'{sheet.title}!{rowcol_to_a1(error_row_index, error_column_index + 1)}'
            sheet.spreadsheet.values_update(
                cell_range_error,
                params={'valueInputOption': 'RAW'},
                body={'values': [[error_messages_str_single_cell]]}
            )
            # chatworkにエラー内容を通知
            message = f"求人情報のアップロードに失敗しました.\n{str(error_messages_str)}\n案件名：{company_name}"
            messages.append(message)
            chatwork = Chatwork(room_id, messages, operator)
            chatwork.send_alert_for_chatwork()
        except Exception as e:
            message = f"エラー内容の記載に失敗しました.\n{str(e)}\n案件名：{company_name}"
            messages.append(error_messages)
            messages.append(message)
            chatwork = Chatwork(room_id, messages, operator)
            chatwork.send_alert_for_chatwork()

    # error_messagesにメッセージが格納されていない場合は以下の処理を走らせる
    else:
        # 最新の求人情報をダウンロードしてきてスプレッドシートに反映
        try:
            # 出稿中の求人を検索してcsvとしてダウンロード
            driver.get(download_url)
            sleep(3)
            # ページ全体のテキストを取得
            page_text = driver.find_element(By.TAG_NAME, 'body').text

            print(page_text)
            mark_checkbox(driver)
            # # driver.save_screenshot('/tmp/test.png')
            # Chatwork_Util.upload_files_request(room_id='356389186', token='aa07226db4f595140cde0323e30948a7',  upload_files_path='/tmp/test.png')

            download_result = download_csv_file(driver)
            print(download_result)

            driver.close()
        except Exception as e:
            message = f"出稿中の求人データの取得に失敗しました.\n{str(e)}\n案件名：{company_name}"
            messages.append(message)
            chatwork = Chatwork(room_id, messages, operator)
            chatwork.send_alert_for_chatwork()

        try:
            file_behind = date_getter()
            # Check if the script is running on AWS Lambda
            if 'win' not in sys.platform:
                filename = f"/tmp/orders_{file_behind}.csv"
            else:
                filename = f"C:/Users/kinoshita-t/Downloads/orders_{file_behind}.csv"
            # filename = f"C:\\Users\\kinoshita-t\\Downloads\\orders_{file_behind}.csv"
            with open(filename, 'r', encoding='CP932') as file:
                reader = csv.DictReader(file)
                # 各行を順に表示
                for row in reader:
                    print(row)
            # シート
            success = write_posted_joblist(sheet,company_name)
            chatwork = Chatwork(room_id, success, operator)
            chatwork.send_alert_for_chatwork()

        except Exception as e:
            message = f"求人の書き込みに失敗しました.\nシートの書き込みを阻害する要素があります。\n{str(e)}\n案件名：{company_name}"
            messages.append(message)
            chatwork = Chatwork(room_id, messages, operator)
            chatwork.send_alert_for_chatwork()
        filename = delete_file()
        print(filename)

if __name__ == '__main__':
    lambda_handler(
        event={
            'sheetId':'1ASZKYDXXCnWKsh4xOs82wlvfMhqIVOIicYZmZ8LbPh8',
            'companyName':'dym'

               },
        context=None)