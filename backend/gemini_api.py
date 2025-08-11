import json, os, requests

def call_gemini_for_suggestion(structured_symptoms, candidate_departments, API_KEY):
    """
    當本地模型信心度不足時，呼叫 Gemini API 進行專家分析。
    """
    if not API_KEY:
        print("錯誤：未提供 Gemini API Key。")
        return {"error": "未配置 API Key"}

    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

    print("本地模型信心度不足，正在請求 Gemini 專家分析...")
    
    prompt = f"""
    你是一位資深、謹慎的台灣急診檢傷分類護理師。你的任務是根據一份結構化的「初步問診摘要」，進行分析並以 JSON 格式回覆。

    **你的分析必須包含以下三個項目：**
    1.  `department`: 從「候選科別列表」中，選擇最適合的一個主要科別。
    2.  `urgency_level`: 根據症狀的嚴重性與潛在風險，評估緊急程度。分為三個等級：「建議盡快就醫」、「可安排門診」、「非緊急」。
    3.  `recommendation_reason`: 用簡短的一句話（不超過30字）解釋你推薦該科別與判斷緊急程度的原因。

    **規則：**
    -   絕對禁止提供任何形式的診斷或醫療建議。你的任務是「分流」與「評估風險」。
    -   如果症狀包含「突然劇痛」、「呼吸困難」、「胸痛」等高風險詞彙，應提高緊急程度。
    -   你的回答必須是標準的 JSON 格式，且只包含上述三個鍵。

    ---
    **候選科別列表：**
    {json.dumps(candidate_departments, ensure_ascii=False)}

    **使用者初步問診摘要：**
    "{structured_symptoms}"
    ---

    請根據以上資訊，生成你的 JSON 分析報告。
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status() # 如果 HTTP 狀態碼是 4xx 或 5xx，這會拋出錯誤
        data = response.json()
        
        raw_text_from_gemini = data['candidates'][0]['content']['parts'][0]['text']
        print(f"從 Gemini 收到的原始回應文字: {raw_text_from_gemini}")

        # 【核心修改】直接解析並回傳整個 JSON 物件
        analysis_result = json.loads(raw_text_from_gemini)
        print(f"Gemini 專家分析結果: {analysis_result}")
        return analysis_result # 回傳完整的分析物件 {'department': '...', 'urgency_level': ...}


    except json.JSONDecodeError as e:
        print(f"解析 Gemini 回應時發生格式錯誤: {e}")
        return {"error": "AI 回應格式錯誤"}
    except requests.exceptions.RequestException as req_err:
        print(f"請求 Gemini API 時發生網路錯誤: {req_err}")
        return {"error": "網路請求失敗"}
    except Exception as e:
        print(f"呼叫 Gemini API 時發生未預期錯誤: {e}")
        return {"error": "發生未預期錯誤"}

# 【新增】用來驗證單輪對話的函式
def call_gemini_for_validation(question, answer, API_KEY):
    """
    驗證使用者的回答是否與問題相關。
    """
    if not API_KEY:
        return {"is_relevant": True, "feedback": ""} # 如果沒有 Key，先假設都通過

    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

    prompt = f"""
    你是一位有耐心、且善於引導的醫療助理。你的任務是判斷使用者的回答是否有效回應了你的問題。

    **規則：**
    - 你的回答必須是 JSON 格式。
    - JSON 中必須包含 `is_relevant` (boolean) 和 `feedback` (string) 這兩個鍵。
    - 如果回答與問題相關，`is_relevant` 應為 `true`，`feedback` 為空字串。
    - 如果回答完全無關（例如問症狀，答天氣），`is_relevant` 應為 `false`，並在 `feedback` 中提供一句簡短、溫和的提醒（繁體中文），引導使用者回到正題。
    - 即使用戶只回答一兩個字，只要相關就算 `true`。例如問持續多久，回答「三天」就算 `true`。

    ---
    **範例 1:**
    問題: "這種不舒服的感覺大概持續多久了？"
    回答: "大概兩三天了"
    你的 JSON 回應: {{"is_relevant": true, "feedback": ""}}

    **範例 2:**
    問題: "除了這個主要症狀，還有沒有其他不舒服的地方？"
    回答: "我今天還沒吃飯"
    你的 JSON 回應: {{"is_relevant": false, "feedback": "不好意思，為了給您更準確的建議，可以請您說明一下除了主要症狀外，還有沒有其他不舒服嗎？"}}
    ---

    **現在請分析以下對話：**

    問題: "{question}"
    回答: "{answer}"

    請生成你的 JSON 分析報告。
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        return json.loads(raw_text)
    except Exception as e:
        print(f"對話驗證時發生錯誤: {e}")
        # 如果 API 出錯，我們就當作回答是有效的，讓對話繼續下去
        return {"is_relevant": True, "feedback": ""}

