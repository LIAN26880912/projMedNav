import json, os, requests

def call_gemini_for_suggestion(symptom_text, candidate_departments, API_KEY):
    """
    當本地模型信心度不足時，呼叫 Gemini API 進行專家分析。
    """
    if not API_KEY:
        print("錯誤：未提供 Gemini API Key。")
        return []

    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

    print("本地模型信心度不足，正在請求 Gemini 專家分析...")
    
    prompt = f"""
    你是一個專業且謹慎的台灣醫療導航助理。你的唯一任務是根據使用者提供的「症狀描述」，從「候選科別列表」中，選擇出最適合的一個科別。

    **規則：**
    1.  絕對禁止提供任何形式的診斷或醫療建議。
    2.  你的回答必須是標準的 JSON 格式。
    3.  JSON 中必須包含一個名為 "department" 的鍵，其值必須是從下方候選科別列表中選出的最適合的科別名稱。

    ---
    **候選科別列表：**
    {json.dumps(candidate_departments, ensure_ascii=False)}

    **使用者症狀描述：**
    "{symptom_text}"
    ---

    請根據以上資訊，生成你的推薦。
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
        
        # 【關鍵修改 1】在解析前，先取出原始文字並印出來
        raw_text_from_gemini = data['candidates'][0]['content']['parts'][0]['text']
        print(f"從 Gemini 收到的原始回應文字: {raw_text_from_gemini}")

        # 【關鍵修改 2】針對 JSON 解析增加更具體的錯誤處理
        try:
            recommended_dept_json = json.loads(raw_text_from_gemini)
            department = recommended_dept_json.get("department")
            
            if department:
                print(f"Gemini 專家分析結果: {department}")
                return [department]
            else:
                print("Gemini 回應中未找到 'department' 鍵。")
                return []
        
        except json.JSONDecodeError as json_err:
            print(f"解析 Gemini 回應時發生 JSON 格式錯誤: {json_err}")
            return []

    except requests.exceptions.RequestException as req_err:
        print(f"請求 Gemini API 時發生網路錯誤: {req_err}")
        return []
    except Exception as e:
        # 這個 Exception 會捕捉到 RecursionError 等其他所有未預期的錯誤
        print(f"呼叫 Gemini API 時發生未預期錯誤: {e}")
        return []