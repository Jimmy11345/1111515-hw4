from flask import Flask, request, jsonify
from pyngrok import ngrok
import os
import json
import google.generativeai as genai

# 載入 LINE Message API 相關函式庫
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import TextSendMessage, ImageSendMessage, VideoSendMessage, LocationSendMessage

# 設定 API 金鑰（你可採用 dotenv 載入 .env 檔）
ACCESS_TOKEN = 'FeUE1PsKhVjaZYFIasURf6Amw1zPsonFOqCVvtPeNmrubRCkuGho1XjsB1FmI0Zzb69LCdC40HzKWd7cMibSnmWdqZ+3kv7d/PWeR8UbT1hyWlWmfKeL+tH84qehPmpekmBibyZ2mgGedrhE/7FHuwdB04t89/1O/w1cDnyilFU='
SECRET = 'd1b3a6f9f8b246034ba21569c9ce09c7'
GEMINI_API_KEY = 'AIzaSyAODcs9bsy2m7VSDGbESTSGtpWkUxItSkE'

# 設定埠號與初始化 Flask 應用
port = 5000
app = Flask(__name__)

# Kill any existing ngrok tunnels before starting a new one
ngrok.kill()

# 開啟 ngrok Tunnel，取得公開 URL，並印出
public_url = ngrok.connect(port).public_url
print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\" ")

# 初始化 LINE API 與 handler
line_bot_api = LineBotApi(ACCESS_TOKEN)
handler = WebhookHandler(SECRET)

# 設定 Gemini API 金鑰
genai.configure(api_key=GEMINI_API_KEY)

# 建立對話歷史資料儲存用的 list
conversation_history = []

# 定義利用 Gemini API 生成 AI 文字的函數
def generate_text(prompt):
    # 注意：這裡使用的是 Gemini 模型，視你申請的 API 與文件可能需要調整參數
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text

# 設定 LINE Webhook 端點，請在 LINE Developers 將 Webhook URL 設為 {ngrok_public_url}/callback
@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_data(as_text=True)
    try:
        signature = request.headers['X-Line-Signature']
        # 由 handler 處理訊息事件
        handler.handle(body, signature)
    except Exception as e:
        print(f"Error: {e}")
    return 'OK'

# 當收到文字訊息事件時，處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip().lower()

    if user_text == 'image':
        output = ImageSendMessage(
            original_content_url='https://engineering.linecorp.com/wp-content/uploads/2020/04/slide_image_01.png',
            preview_image_url='https://engineering.linecorp.com/wp-content/uploads/2020/04/slide_image_01.png'
        )

    elif user_text == 'video':
        output = VideoSendMessage(
            original_content_url='https://static.line-scdn.net/myhome/bg/line_home_cover_video.mp4',
            preview_image_url='https://static.line-scdn.net/myhome/bg/line_home_cover_preview.png'
        )

    elif user_text == 'location':
        output = LocationSendMessage(
            title='Mask Map',
            address='花蓮市',
            latitude=23.601916,
            longitude=121.518989
        )

    else:
        # 其他文字交由 Gemini AI 回覆
        ai_text = generate_text(user_text)
        conversation_history.append({"user": user_text, "bot": ai_text})
        output = TextSendMessage(text=ai_text)

    # 回覆用戶
    line_bot_api.reply_message(
        event.reply_token,
        output
    )

# 提供 RESTful API 來取得對話歷史
@app.route("/history", methods=["GET"])
def get_history():
    return jsonify(conversation_history)

# 提供 RESTful API 來刪除對話歷史
@app.route("/history", methods=["DELETE"])
def clear_history():
    conversation_history.clear()
    return jsonify({"status": "deleted"})

# 啟動 Flask 伺服器
if __name__ == "__main__":
    app.run(port=port)
