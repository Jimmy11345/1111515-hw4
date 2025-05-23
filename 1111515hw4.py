from flask import Flask, request, jsonify
from pyngrok import ngrok
import os
import json
import google.generativeai as genai
from linebot.models import FlexSendMessage
from linebot.models import StickerSendMessage
import requests

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import TextSendMessage, ImageSendMessage, VideoSendMessage, LocationSendMessage


ACCESS_TOKEN = 'FeUE1PsKhVjaZYFIasURf6Amw1zPsonFOqCVvtPeNmrubRCkuGho1XjsB1FmI0Zzb69LCdC40HzKWd7cMibSnmWdqZ+3kv7d/PWeR8UbT1hyWlWmfKeL+tH84qehPmpekmBibyZ2mgGedrhE/7FHuwdB04t89/1O/w1cDnyilFU='
SECRET = 'd1b3a6f9f8b246034ba21569c9ce09c7'
GEMINI_API_KEY = 'AIzaSyAODcs9bsy2m7VSDGbESTSGtpWkUxItSkE'


port = 5000
app = Flask(__name__)


ngrok.kill()

# 開啟 ngrok Tunnel，取得公開 URL，並印出
public_url = ngrok.connect(port).public_url
print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\" ")


line_bot_api = LineBotApi(ACCESS_TOKEN)
handler = WebhookHandler(SECRET)


genai.configure(api_key=GEMINI_API_KEY)


conversation_history = []

city_map = {
    '台北': 'Taipei',
    '台中': 'Taichung',
    '台南': 'Tainan',
    '高雄': 'Kaohsiung',
    '新竹': 'Hsinchu',
    '桃園': 'Taoyuan'
}

def get_weather(city_name):
    api_key = '295e4f86026949443d221dc2413a87eb'
    city_query = city_map.get(city_name, city_name)
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_query}&appid={api_key}&lang=zh_tw&units=metric"

    response = requests.get(url)
    if response.status_code != 200:
        return f"⚠️ 查詢失敗（{response.status_code}）：{response.text}"

    data = response.json()
    name = data['name']
    weather = data['weather'][0]['description']
    temp = data['main']['temp']
    humidity = data['main']['humidity']
    wind = data['wind']['speed']

    return f"""📍 {name} 天氣
🌤 狀況：{weather}
🌡 溫度：{temp}°C
💧 濕度：{humidity}%
💨 風速：{wind} m/s"""

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

# 當收到訊息事件時，處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip().lower()

    if user_text == 'image':
        output = ImageSendMessage(
            original_content_url='https://i.imgur.com/2nCt3Sbl.jpg',
            preview_image_url='https://i.imgur.com/2nCt3Sb.jpg'
        )
    elif user_text == 'sticker':
        output = StickerSendMessage(
            package_id='1',
            sticker_id='1'
        )
    elif user_text == 'video':
        output = VideoSendMessage(
            original_content_url='https://media.w3.org/2010/05/sintel/trailer.mp4',
            preview_image_url='https://i.imgur.com/2nCt3Sb.jpg'
        )

    elif user_text == 'location':
        output = LocationSendMessage(
            title='Mask Map',
            address='花蓮市',
            latitude=23.601916,
            longitude=121.518989
        )
    elif user_text == 'flex':
        output = FlexSendMessage(
            alt_text='hello',
            contents={
                'type': 'bubble',
                'direction': 'ltr',
                'hero': {
                    'type': 'image',
                    'url': 'https://engineering.linecorp.com/wp-content/uploads/2021/04/%E6%96%B0LINE_BLOG_EN.png',
                    'size': 'full',
                    'aspectRatio': '100:100',
                    'aspectMode': 'cover',
                    'action': {
                        'type': 'uri',
                        'uri': 'http://example.com',
                        'label': 'Label'
                    }
                }
            }
        )
    elif user_text.startswith("weather"):
      parts = user_text.split(" ", 1)
      if len(parts) == 2:
        city = parts[1]
        weather_report = get_weather(city)
      else:
        weather_report = "請輸入城市，例如：weather 台北"
      output = TextSendMessage(text=weather_report)

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
