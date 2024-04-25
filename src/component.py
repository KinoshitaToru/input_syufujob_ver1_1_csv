import os
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
import glob
import pdb
import sys


login_url = "https://part.shufu-job.jp/console/login"
upload_url = "https://part.shufu-job.jp/console/c_orders/upload"
download_url = "https://part.shufu-job.jp/console/c_orders/search"

# （あなたのサービスアカウント用）Google APIに接続
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('service.json', scope)
client = gspread.authorize(creds)

# スプレッドシートを開き、タブを指定
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ASZKYDXXCnWKsh4xOs82wlvfMhqIVOIicYZmZ8LbPh8/edit#gid=1937027335'  # Replace with your URL
spreadsheet_id = spreadsheet_url.split('/d/')[1].split('/edit')[0]

# Open the Spreadsheet with the ID
spreadsheet = client.open_by_key(spreadsheet_id)
sheet = spreadsheet.worksheet("dym")

def clear_tmp_directory():
    files = glob.glob('/tmp/*')
    for f in files:
        os.remove(f)

def get_driver(chrome_options: Options) -> webdriver:
    if 'win' not in sys.platform:
        # AWS Lambda
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-dev-tools')
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory":  '/tmp',
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        chrome_options.binary_location = '/opt/chrome/chrome'
        s = Service(executable_path='/opt/chromedriver')
        driver = webdriver.Chrome(service=s, options=chrome_options)
    else:
        s = Service(executable_path=r'C:\web_driver\chromedriver-win64\chromedriver.exe')
        driver = webdriver.Chrome(service=s, options=chrome_options)

    print('クロームドライバ取得OK')
    return driver

def login(driver, account_id, account_ps, login_url):
    driver.get(login_url)
    sleep(1)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'login-name')))
    driver.find_element(By.ID, "login-name").send_keys(account_id)
    driver.find_element(By.ID, "login-pass").send_keys(account_ps)
    login_button_element = driver.find_element(By.NAME, "login")
    login_button_element.click()
    sleep(1)
    print("ログイン完了")

# ファイルをrequestを用いてuploadする方法
# def upload_file_by_request(driver, upload_url, csv_file_path):
#     request_url = "https://part.shufu-job.jp/console/api_c_orders/execImport.json"
#
#     error_messages = []
#     driver.get(upload_url)
#     sleep(10)
#     popup = pop_up_dealer(driver)
#     print(popup)
#     input_element = driver.find_element(By.CSS_SELECTOR, 'input.inputFile')
#     input_element.send_keys(csv_file_path)
#     sleep(10)



# ファイルをアップロードするロジック
def upload_csv_file(driver, upload_url, csv_file_path):
    # ファイルをアップロードするページに遷移
    error_messages = []
    driver.get(upload_url)
    sleep(10)
    popup = pop_up_dealer(driver)
    print(popup)
    print(driver.page_source)
    input_element = driver.find_element(By.CSS_SELECTOR, 'input.inputFile')
    input_element.send_keys(csv_file_path)
    # driver.refresh()
    sleep(10)
    # driver.refresh()
    text = driver.find_element(By.ID, 'upload').text
    print(text)
    # if "登録" in text:
    #     pass
    # else:
    #     msg = "ファイルの登録に失敗しました"
    #     msg2 = "ファイルの登録の画面が変更された可能性があります"
    #     error_messages.append(msg)
    #     error_messages.append(msg2)
    #     return error_messages
    sleep(3)
    popup = pop_up_dealer(driver)
    print(popup)
    upload_element = driver.find_element(By.CSS_SELECTOR,'span[id=upload]')
    sleep(3)
    driver.execute_script("arguments[0].click();", upload_element)
    sleep(50)
    register_element_text = driver.find_element(By.ID, 'register').text

    if 'エラー' in register_element_text:
        td_elements = driver.find_elements(By.XPATH,'//tbody[@id="register"]//td')
        for td in td_elements:
            error_messages.append(td.text)

    elif '完了' in register_element_text:
        pass

    else:
        error_messages.append("想定していないエラーがファイルアップロードの際に発生しました")
        error_messages.append("想定していないエラーがファイルアップロードの際に発生しました。\nファイルアップロードの画面の仕様が変わったことも考えられます。")
        kill = driver.find_element(By.CSS_SELECTOR, 'span.btn.btn-danger.btn-embossed.btn-file.fileinput-exists')
        sleep(1)
        driver.execute_script("arguments[0].click();", kill)
        sleep(1)
        confirmations = driver.execute_script("document.querySelectorAll('div[class=modal-footer] a')[1].click()")
        sleep(1)
        if "中止" in register_element_text:
            error_messages.append("中止完了")


    return error_messages

def mark_checkbox(driver):
    # すべてを選択するチェックボックスを探し出す
    checkbox = driver.find_element(By.ID,"all_checked_button")
    print(checkbox)
    driver.execute_script("arguments[0].click();", checkbox)
    sleep(1)

def list_files(directory):
    return os.listdir(directory)
def download_csv_file(driver):
    span_element = driver.find_element(By.CSS_SELECTOR, "span[id=csv_download]")
    driver.execute_script("arguments[0].click();", span_element)
    sleep(30)
    pop_up_dealer(driver)
    download_button = driver.find_element(By.ID, "downloadButton")

    if 'win' not in sys.platform:
        files = list_files('/tmp')
    else:
        files = list_files("C:/Users/kinoshita-t/Downloads")

    if download_button:
        sleep(10)
        download_button = driver.find_element(By.CSS_SELECTOR, 'div[class=button_area] a')

        driver.execute_script("arguments[0].click();", download_button)
        sleep(40)  # make sure the download has finished
        if 'win' not in sys.platform:
            files = list_files('/tmp')
        else:
            files = list_files("C:/Users/kinoshita-t/Downloads")
        return files
    else:
        return "ダメだった"

def pop_up_dealer(driver):
    try:
        sleep(1)
        if driver.find_element(By.CSS_SELECTOR, ".g-modal-pos .g-modal-size"):
            button = driver.find_element(By.CSS_SELECTOR, ".g-modal-pos .g-modal-size .gFooter .gBtn.g-modal-next")
            driver.execute_script("arguments[0].click();", button)
            return "ポップアップあった"
    except NoSuchElementException:
        return "ポップアップなかった"

def tab_counter(driver):
    list_count = driver.find_element(By.CSS_SELECTOR, "div[class=mbl] div[class=list_count]")
    list_count_text = list_count.text
    # "件中"の手前にある数字部分を抜き出す
    match = re.search(r'(\d+)件中', list_count_text)
    if match:
        number = match.group(1)
        # "number" を整数に変換します。
        number = int(number)

    # 30 で除算し、その結果を切り捨てて整数部分を求めます。
    quotient = number // 30
    # "number" を 30 で割った余りを求めます。
    remainder = number % 30

    if remainder == 0:
        result = quotient
    else:
        result = quotient + 1

    return result

def date_getter():
    # 現在の年月日を取得
    today = datetime.today()

    # 年、月、日を取得
    year = today.year
    month = f"{today.month:02d}"    # 0でパディングされた2桁の整数に変換
    day = f"{today.day:02d}"        # 0でパディングされた2桁の整数に変換

    file_behind = f"{year}{month}{day}"
    return file_behind

def get_account_data(spreadsheet_id, company_name):
    # Open the Spreadsheet with the ID
    workbook = client.open_by_key(spreadsheet_id)
    worksheet = workbook.worksheet('マスター')
    print(f'ワークシートURL: {worksheet.url}')
    all_data = worksheet.get_all_values()
    header_row = all_data[0]
    header_to_index = {header: index for index, header in enumerate(header_row)}

    if 'company_id' in header_to_index and 'account_id' in header_to_index and 'account_ps' in header_to_index:

        company_id_index = header_to_index['company_id']
        account_id_index = header_to_index['account_id']
        account_ps_index = header_to_index['account_ps']
        account_op_index = header_to_index['operator']

        matching_row = [row for row in all_data if row[company_id_index] == company_name]
        print('company_nameと一致するcompany_idを発見')

        if matching_row:
            matching_row = matching_row[0]  # take the first match
            account_id = matching_row[account_id_index]
            account_ps = matching_row[account_ps_index]
            operator = matching_row[account_op_index]
            print('マスターから必要情報を取得')
        else:
            account_id = None
            account_ps = None
            operator = None

    else:
        return('Necessary headers not found.')

    if account_id and account_ps and operator:
        return account_id, account_ps, operator

def mark_all_checkbox(driver):
    # ファイルをダウンロードするページに遷移
    sleep(3)
    popup = pop_up_dealer(driver)
    print(popup)
    result = tab_counter(driver)
    # loop_count = int(result) - 1
    # print(loop_count)
    for _ in range(result):
        try:
            sleep(1)
            popup = pop_up_dealer(driver)
            print(popup)
            mark_checkbox(driver)

            # 遷移するボタンを見つけ出す
            next_page_button = driver.find_element(By.CSS_SELECTOR, 'div[class="pagination mb0"] li[class="next"] a')
            driver.execute_script("arguments[0].click();", next_page_button) # 次のページへ遷移
            sleep(1)  # ページが完全に読み込まれるまで待つ
        except NoSuchElementException:  # 要素がなければループを抜ける
            print("No more element")
            break

# def mark_all_checkbox2(driver):
#     sleep(3)
#     popup = pop_up_dealer(driver)
#     print(popup)
#     selector_all = driver.execute_script("document.querySelector('button[id=all_checked_button]')")
#     if selector_all:
#         driver.execute_script("document.querySelector('button[id=all_checked_button]').click()")
#     else:
#         print("No more element")

def csv_checker():
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

def write_posted_joblist(sheet, company_name):
    error_message = []
    file_behind = date_getter()
    # Check if the script is running on AWS Lambda
    if 'win' not in sys.platform:
        filename = f"/tmp/orders_{file_behind}.csv"
    else:
        filename = f"C:/Users/kinoshita-t/Downloads/orders_{file_behind}.csv"
    # filename = f"C:\\Users\\kinoshita-t\\Downloads\\orders_{file_behind}.csv"
    with open(filename, 'r', encoding='CP932') as file:
        reader = csv.DictReader(file)
        print(reader)
        data = [row for row in reader]
    # データを列単位の辞書に再構成
    col_data = {header: [row[header] for row in data] for header in data[0].keys()}
    # スプレッドシートのヘッダとCSVのヘッダを比較
    spreadsheet_headers = sheet.row_values(1)  # ヘッダが1行目にあると仮定

    #　転記ステータスに済を追加する
    status_header = "転記ステータス"
    status_value = "済"
    status_column = spreadsheet_headers.index(status_header) + 1 if status_header in spreadsheet_headers else None

    # エラー内容に空を追加するメソッド
    error_header = "エラー内容"
    error_value = ""  # Set the value you want to insert
    error_column = spreadsheet_headers.index(error_header) + 1 if error_header in spreadsheet_headers else None

    # CSVのヘッダとスプレッドシートのヘッダを比較し、各ヘッダーの値を更新
    cells_to_update = []
    for index, header in enumerate(spreadsheet_headers):
        if header in col_data.keys():  # Only proceed if the header is found in the CSV data
            for i, value in enumerate(col_data[header]):
                # Add 2 to the row index because spreadsheet row indices are 1-based and the header is on the first row
                cells_to_update.append(gspread.Cell(row=i+2, col=index+1, value=value))

                # Also update "転記ステータス" column
                if status_column:
                    cells_to_update.append(gspread.Cell(row=i + 2, col=status_column, value=status_value))

                # Also update "エラー内容" column
                if error_column:
                    cells_to_update.append(gspread.Cell(row=i + 2, col=error_column, value=error_value))

    # バッチでセルを更新
    try:
        response = sheet.update_cells(cells_to_update)
    except gspread.exceptions.GSpreadException as e:
        if 'PERMISSION_DENIED' in str(e):
            exception = f"サービスアカウントへの編集権限が付与されておりません.\n{str(e)}\n案件名：{company_name}"
            print(exception)
            error_message.append(exception)
        elif 'edit a protected cell or object' in  str(e):
            exception = f"スプレッドシートの一部のセルが保護されている可能性があります.\n{str(e)}\n案件名：{company_name}"
            print(exception)
            error_message.append(exception)
        else:
            # エラーが発生した場合、そのエラーメッセージを出力
            exception = f"スプレッドシートに書き込む際のエラー: {e}\n 案件名：{company_name}"
            print(exception)
            error_message.append(exception)
    else:
        # sheet.update_cellsがエラーを発生させなかったので、
        # セルの更新が成功したと見なす
        exception = f"転記成功\n 案件名：{company_name}"
        print(exception)
        error_message.append(exception)
    # レート制限を避けるため、リクエスト間に遅延を入れる
    sleep(1)

    return error_message

def delete_file():
    file_behind = date_getter()
    if 'win' not in sys.platform:
        filename = f"/tmp/orders_{file_behind}.csv"
    else:
        filename = f"C:/Users/kinoshita-t/Downloads/orders_{file_behind}.csv"
    # directoryがファイルである場合、削除
    if os.path.isfile(filename):
        os.remove(filename)
    else:
        print(f'Error: {filename} is not a file')

    return filename


# spreadsheet_id = "1ASZKYDXXCnWKsh4xOs82wlvfMhqIVOIicYZmZ8LbPh8"
#
# company_name = 'dym'
#
# mastersheet_id = "1813MXeKilK4IPKrS6xleElMVA2Tt1r3-QiMcelqxB58"
#
# login_url = "https://part.shufu-job.jp/console/login"
# upload_url = "https://part.shufu-job.jp/console/c_orders/upload"
# download_url = "https://part.shufu-job.jp/console/c_orders/search"

# # （あなたのサービスアカウント用）Google APIに接続
# scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# creds = ServiceAccountCredentials.from_json_keyfile_name('service.json', scope)
# client = gspread.authorize(creds)
# #
# # Open the Spreadsheet with the ID
# spreadsheet = client.open_by_key(spreadsheet_id)
# sheet = spreadsheet.worksheet(company_name)
# # #
# # # # ワークシートのデータを取り出す
# # # data = sheet.get_all_values()
# # #
# # # # データを DataFrame に転送
# # # df = pd.DataFrame(data[1:], columns=data[0])  # Assuming first row is column names
# # # print(df)
# # #
# # # # "転記ステータス"列で値が"済"でない行を抽出
# # # df = df[df['転記ステータス'] == '']
# # # print(df)
# # #
# # # # A～CQ列を選択（列名で指定）
# # # columns = list(df.columns)[:103]  # Adjust the number as needed
# # # df = df[columns]
# csv_file_name = company_name + ".csv"
# input_file_path = f"C:/Users/kinoshita-t/Downloads/{csv_file_name}"
# # # # input_file_path = os.path.join("C:", "Users", "kinoshita-t", "Downloads", csv_file_name).replace('\ ', '/')
# # #
# # # # DataFrame を CSV ファイルに出力
# # # df.to_csv(input_file_path, sep=',', encoding='CP932', index=False)
# # #
# # mastersheetからアイパスを取得
# account_id, account_ps, operator = get_account_data(mastersheet_id, company_name)
# print(account_id, account_ps)
# # #
# chrome_options = Options()
# driver = get_driver(chrome_options)
# #
# # ログイン
# login(driver, account_id, account_ps, login_url)
# sleep(3)
# #
# # data_dict = {}  # 結果を保管するための辞書
# driver.get(download_url)
# sleep(3)
# # ページ全体のテキストを取得
# page_text = driver.find_element(By.TAG_NAME, 'body').text
#
# print(page_text)
#
# driver.quit()
# #
# # ログイン
# login(driver, account_id, account_ps, login_url)
# #
# # ファイルをアップロード
# df = pd.DataFrame(data[1:], columns=data[0])
# error_messages = upload_csv_file(driver, upload_url, input_file_path)
# # num_rows = sheet.row_count  # 現在の行数を取得する
# # error_column_index = df.columns.to_list().index('エラー内容')
# # error_row_index = ""
# # if error_messages:
# #     print(error_messages)
# #     for message in error_messages:
# #         match = re.search(r'(\d+)行目', message)
# #         if match:
# #             error_row_index = int(match.group(1))
# #         else:
# #             error_row_index = 2
# #             print ('error_row_indexが取得できませんでした')
# #     if error_messages:
# #         range_start = rowcol_to_a1(2, error_column_index + 1)  # convert into A1 notation
# #         range_end = rowcol_to_a1(num_rows + 1, error_column_index + 1)
# #         cell_range = f'{sheet.title}!{range_start}:{range_end}'  # Add 'Worksheet' name into A1 notation
# #
# #         sheet.spreadsheet.values_update(  # Call 'values_update' in the Spreadsheet instance
# #             cell_range,
# #             params={'valueInputOption': 'RAW'},
# #             body={'values': [[""]] * num_rows}
# #         )
# #     # write new error message into the specific cell
# #     error_messages_str = error_messages[1]  # Assuming that error_messages contains only one item
# #     print(error_messages_str)
# #     error_messages_lines = error_messages_str.split("\n")
# #     error_messages_str_single_cell = "\n".join(error_messages_lines)
# #     cell_range_error = f'{sheet.title}!{rowcol_to_a1(error_row_index, error_column_index + 1)}'
# #     sheet.spreadsheet.values_update(
# #         cell_range_error,
# #         params={'valueInputOption': 'RAW'},
# #         body={'values': [[error_messages_str_single_cell]]}
# #     )
# # else:
# 出稿中の求人を検索してcsvとしてダウンロード
# # driver.get(download_url)
# mark_checkbox(driver)
# download_button = download_csv_file(driver)
# print(download_button)
#
# driver.close()
#
# シート
# write_posted_joblist(sheet)




# worksheet = spreadsheet.get_worksheet(0)
# # Get the name of the first tab
# first_tab_name = spreadsheet.sheet1.title
# print(first_tab_name)
#
# # ワークシートのデータを取り出す
# data = worksheet.get_all_values()
#
# # データを DataFrame に転送
# df = pd.DataFrame(data[1:], columns=data[0])  # Assuming first row is column names
#
# # "転記ステータス"列で値が"済"でない行を抽出
# df = df[df['転記ステータス'] != '']
#
# # A～CQ列を選択（列名で指定）
# columns = list(df.columns)[:87]  # Adjust the number as needed
# df = df[columns]
#
# # DataFrame を CSV ファイルに出力
# df.to_csv(r'C:\Users\kinoshita-t\test_csv\test.csv', encoding='utf-8-sig', index=False)
