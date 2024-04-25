import os
import requests

class Chatwork_Util:
    # コンストラクタ
    def __init__(self, token):
        self._token = token
        self._room_mambers_dict = {}
        self._session = requests.session()
    
    # ルームごとのメンバー一覧の辞書
    @property
    def room_mambers_dict(self):
        return self._room_mambers_dict

    # メッセージ送信（クラスメソッド）
    @classmethod
    def send_message_request(self, room_id, token, body, session=None):
        url = f'https://api.chatwork.com/v2/rooms/{room_id}/messages'
        try:
            data    = {'body': body, 'self_unread': 1}
            headers = {'X-ChatWorkToken': token}
            if session:
                res = session.post(url, data=data, headers=headers)
            else:
                res = requests.post(url, data=data, headers=headers)
            return res
        except Exception as e:
            print(f'メッセージ送信失敗\n{e}')
            return e
       
    # メッセージ送信
    def send_message(self, room_id, body):
        return self.send_message_request(room_id, self._token, body, self._session)
       
    # ファイル送信（クラスメソッド）
    @classmethod
    def upload_files_request(self, room_id, token, upload_files_path, session=None):
        if not upload_files_path: return False
        url = f'https://api.chatwork.com/v2/rooms/{room_id}/files'
        try:
            files   = {'file': open(os.path.abspath(upload_files_path), 'rb')}
            headers = {"X-ChatWorkToken": token}
            if session:
                res = session.post(url, headers=headers, files=files)
            else:
                res = requests.post(url, headers=headers, files=files)
            return res
        except Exception as e:
            print(f'ファイル送信失敗\n{e}')
            return e
    
    # ファイル送信
    def upload_files(self, room_id, upload_files_path):
        return self.upload_files_request(room_id, self._token, upload_files_path, self._session)

    # ルームのメンバー一覧取得（クラスメソッド）
    @classmethod
    def get_room_members_request(self, room_id, token, session=None):
        url = f'https://api.chatwork.com/v2/rooms/{room_id}/members'
        try:
            headers = {'X-ChatWorkToken': token}
            if session:
                res = session.get(url, headers=headers)
            else:
                res = requests.get(url, headers=headers)
            if res.status_code != 200: raise Exception(f'{res.json()}')
            member_list = res.json()
            member_dict = {f'{mamber.get("account_id")}': mamber.get('name') for mamber in member_list} 
            return member_dict
        except Exception as e:
            print(f'メンバー一覧取得失敗\n{e}')
            return {}

    # ルームのメンバー一覧取得
    def get_room_members(self, room_id, reload=False): 
        if (member_dict := self._room_mambers_dict.get(str(room_id))) and not reload:
            return member_dict
        member_dict = self.get_room_members_request(room_id, self._token, self._session)
        self._room_mambers_dict[str(room_id)] = member_dict
        return member_dict
