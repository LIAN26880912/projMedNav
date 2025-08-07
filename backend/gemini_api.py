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
        response.raise_for_status()
        data = response.json()
        
        # 解析 Gemini 回傳的 JSON 字串
        recommended_dept_json = json.loads(data['candidates'][0]['content']['parts'][0]['text'])
        department = recommended_dept_json.get("department")
        
        if department:
            print(f"Gemini 專家分析結果: {department}")
            return [department]
        return []
    except Exception as e:
        print(f"呼叫 Gemini API 時發生錯誤: {e}")
        return []


