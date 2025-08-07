# gemini_api.py

import requests
import json

def call_gemini_for_suggestion(symptom_text, candidate_departments, API_KEY):
    """
    這是一個極簡化的測試版本，用來診斷核心連線問題。
    """
    if not API_KEY:
        print("錯誤：未提供 Gemini API Key。")
        return []

    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

    # --- 【極簡化測試 payload】 ---
    # 我們完全不使用傳入的參數，只用一個最簡單的 "你好" 來測試
    minimal_payload = {
        "contents": [{"parts": [{"text": "你好"}]}]
    }
    print("!!! 正在執行極簡化連線測試 !!!")

    try:
        print("準備發送極簡請求...")
        # 設定 15 秒的超時，避免卡住
        response = requests.post(GEMINI_API_URL, json=minimal_payload, timeout=15)
        print("極簡請求已發送，準備印出回應...")

        # 如果請求成功發送並收到回應，我們將看到以下日誌
        print("="*40)
        print(f"極簡測試 - 回應狀態碼: {response.status_code}")
        print(f"極簡測試 - 回應純文字: {response.text}")
        print("="*40)

        # 既然是測試，我們直接回傳一個固定值，讓前端知道發生了什麼
        return ["測試成功，但目前為除錯模式"]

    except Exception as e:
        print(f"在極簡測試中發生錯誤: {e}")
        return ["測試失敗"]