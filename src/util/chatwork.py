import requests


class Chatwork():
    def __init__(self, id: str, message: list, operator: str) -> None:
        """ChatWorkで 通知する

        Args:
            id (str): _description_
            message (str): _description_
        """

        self.id = id
        self.message = message

        # サービス
        self.service_name = "Chatwork"
        self.end_point = f"https://api.chatwork.com/v2/rooms/{self.id}/messages"

        # postする情報成形
        self.forming_headers()
        self.forming_body(operator)
        self.forming_options()

    def forming_headers(self):
        self.headers = {
            'X-ChatWorkToken': 'aa07226db4f595140cde0323e30948a7',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    def forming_body(self, operator: str):
        self.body = operator + '\n'
        self.body += 'しゅふジョブ　求人内容登録 についての通知\n'
        for msg in self.message:
            self.body += '[code]'
            self.body += "{0}".format(msg)
            self.body += '[/code]\n'
        self.body += '\n\n'

    def forming_options(self):
        self.options = {
            'body': self.body,
            'self_unread': 1
        }

    # Chatworkへ通知するメソッド
    def send_alert_for_chatwork(self):
        """
        chatworkに通知するリクエスト送る
        """
        requests.post(
            url=self.end_point,
            headers=self.headers,
            data=self.options
        )


if __name__ == "__main__":
    messages = ["Error 1", "Error 2", "Error 3"]
    chatwork = Chatwork("356389186", messages, "[To:8208641]木下　暢さん")
    print(chatwork.send_alert_for_chatwork())