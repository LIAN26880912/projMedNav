import json, os, requests

# --- Constants ---
GEMINI_FLASH_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
GEMINI_PRO_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"


# --- MCP Component 1: Gemini-Flash as Dialogue Manager ---
def call_gemini_for_symptom_extraction(conversation_history: str, api_key: str):
    """
    [控制層] 呼叫 Gemini-Flash API 扮演對話管理員。
    它的任務是從自然語言對話中，抽取出結構化的症狀資訊。
    """
    if not api_key:
        return {"error": "未提供 Gemini API Key"}

    api_url = f"{GEMINI_FLASH_API_URL}?key={api_key}"
    
    prompt = f"""
    你是一位專業的問診助理。你的任務是根據以下的對話紀錄，抽取出關鍵的醫療資訊，並統一回傳於 JSON 結構。
    請嚴格按照指定的 JSON 格式回傳，不要添加任何額外的解釋。

    對話紀錄:
    ---
    {conversation_history}
    ---

    請輸出 JSON 格式（所有欄位都要有，未知請填空字串或空陣列）：
    {{
        "symptoms": ["症狀一", "症狀二", "..."],
        "symptom_location": "症狀發生的主要位置 (例如：左下腹、頭部)",
        "symptom_onset": "症狀開始發作的時機或情境 (例如：吃完飯後、早上起床時)",
        "symptom_intensity": "症狀的強度描述 (例如：悶痛、劇痛、1-10分)",
        "duration_days": (數字, 如果未知請填 0),
        "age": "年齡（數字或空字串）",
        "gender": "性別（男/女/空字串）",
        "medical_history": ["個人相關病史1", "過敏史1", "若使用者明確說沒有，請填入'無'"],
        "is_info_complete": (布林值, true 或 false, 如果所有主要欄位都已描述就設為 true，否則為 false)
    }}
    """

    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
        }
    }

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        # print("Gemini Flash raw response:", response.text)  # 原始 API 回應
        outer_response = response.json()
        inner_json_str = outer_response['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(inner_json_str)
        print("Gemini Flash parsed result:", result)        # 解析後的 JSON
        return result
    except requests.exceptions.RequestException as e:
        print(f"呼叫 Gemini API 失敗: {e}")
        return {"error": f"呼叫 Gemini API 失敗: {e}"}
    except (json.JSONDecodeError, KeyError, IndexError) as e: # 增加更多錯誤捕捉
        print(f"解析 Gemini 回應失敗: {e}")
        print(f"原始回應: {response.text}") # type: ignore
        return {"error": f"解析 Gemini 回應失敗"}


# --- MCP Component 2: Gemini-Pro as Medical Expert ---
# --- 疾病推論 Agent ---
def guess_disease_from_gemini_pro_A(structured_symptoms: dict, api_key: str):
    """
    ExpertA: 保守型疾病推論。
    """
    if not api_key:
        return {"error": "未提供 Gemini API Key"}
    api_url = f"{GEMINI_PRO_API_URL}?key={api_key}"
    symptoms_str = ', '.join(structured_symptoms.get('symptoms', ['未提供']))
    duration_str = structured_symptoms.get('duration_days', '未知')
    history_str = ', '.join(structured_symptoms.get('medical_history', ['無']))
    prompt = f"""
你是A型專家，台灣資深醫師，請根據下方結構化症狀摘要，推論最可能的疾病（JSON格式）：
- disease: 疾病名稱（繁體中文）
- reason: 推論理由（繁體中文）
症狀: {symptoms_str}
持續: {duration_str} 天
病史: {history_str}
範例：
{{
    "disease": "感冒",
    "reason": "症狀為流鼻水、咳嗽，持續2天，無特殊病史，最可能為感冒。"
}}
"""
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1,
        }
    }
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        outer = response.json()
        inner_json_str = outer['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(inner_json_str)
        result["source"] = "Gemini-Pro-A"
        return result
    except Exception as e:
        print(f"Gemini Pro 疾病推論A失敗: {e}")
        return {"error": f"Gemini Pro 疾病推論A失敗: {str(e)}"}

def guess_disease_from_gemini_pro_B(structured_symptoms: dict, api_key: str):
    """
    ExpertB: 積極型疾病推論。
    """
    if not api_key:
        return {"error": "未提供 Gemini API Key"}
    api_url = f"{GEMINI_PRO_API_URL}?key={api_key}"
    symptoms_str = ', '.join(structured_symptoms.get('symptoms', ['未提供']))
    duration_str = structured_symptoms.get('duration_days', '未知')
    history_str = ', '.join(structured_symptoms.get('medical_history', ['無']))
    prompt = f"""
你是B型專家，台灣資深醫師，請根據下方結構化症狀摘要，積極推論最可能的疾病（JSON格式）：
- disease: 疾病名稱（繁體中文）
- reason: 推論理由（繁體中文）
症狀: {symptoms_str}
持續: {duration_str} 天
病史: {history_str}
範例：
{{
    "disease": "過敏性鼻炎",
    "reason": "症狀為流鼻水、打噴嚏，病史有過敏，最可能為過敏性鼻炎。"
}}
"""
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.25,
        }
    }
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        outer = response.json()
        inner_json_str = outer['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(inner_json_str)
        result["source"] = "Gemini-Pro-B"
        return result
    except Exception as e:
        print(f"Gemini Pro 疾病推論B失敗: {e}")
        return {"error": f"Gemini Pro 疾病推論B失敗: {str(e)}"}
# 載入科別列表 (此部分維持不變)
try:
    with open(os.path.join(os.path.dirname(__file__), "departments_list.json"), "r", encoding="utf-8") as f:
        departments_list = json.load(f)
except FileNotFoundError:
    print("警告：找不到 departments_list.json，將使用預設科別列表。")
    departments_list = ["家庭醫學科", "內科", "外科", "兒科", "婦產科", "骨科", "皮膚科", "耳鼻喉科", "眼科"]


def get_expert_suggestion_from_gemini_pro(structured_symptoms: dict, api_key: str):
    """
    [專家層] 呼叫 Gemini-Pro API 扮演醫療專家。
    它接收由第一層（控制層）整理好的結構化症狀，進行深度分析並回傳分診建議。
    """
    if not api_key:
        return {"error": "未提供 Gemini API Key"}

    api_url = f"{GEMINI_PRO_API_URL}?key={api_key}"

    symptoms_str = ', '.join(structured_symptoms.get('symptoms', ['未提供']))
    duration_str = structured_symptoms.get('duration_days', '未知')
    history_str = ', '.join(structured_symptoms.get('medical_history', ['無']))
    dept_list_str = ', '.join(departments_list)

    prompt = f"""
你是分診專家，台灣資深醫師，請根據下方結構化症狀摘要，回覆分診建議（JSON格式）：
- urgency_level: '建議盡快就醫', '可安排門診', '非緊急'
- suggested_departments: 嚴格從 [{dept_list_str}] 選（最多3個）
- reason: 一句繁體中文說明
症狀: {symptoms_str}
持續: {duration_str} 天
病史: {history_str}
範例：
{{
    "urgency_level": "非緊急",
    "suggested_departments": ["家庭醫學科"],
    "reason": "症狀屬於一般不適，建議先由家庭醫學科評估。"
}}
"""

    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        outer = response.json()
        inner_json_str = outer['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(inner_json_str)
        print("Gemini Pro (single agent) parsed result:", result)
        return result
    except requests.exceptions.RequestException as e:
        print(f"呼叫 Gemini Pro API 失敗: {e}")
        return {"error": f"呼叫 Gemini Pro API 失敗: {e}"}
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"解析 Gemini Pro 回應失敗: {e}")
        print(f"原始回應: {response.text if 'response' in locals() else 'No response'}")
        return {"error": f"解析 Gemini Pro 回應失敗"}


# --- Multi-Agent 分診專家 ---
def get_expert_suggestion_from_gemini_pro_B(structured_symptoms: dict, api_key: str):
    """
    ExpertB: 積極型 prompt，強調全面考量、避免漏診。
    """
    if not api_key:
        return {"error": "未提供 Gemini API Key"}
    api_url = f"{GEMINI_PRO_API_URL}?key={api_key}"
    # 疾病推論
    disease_result = guess_disease_from_gemini_pro_B(structured_symptoms, api_key)
    disease_name = disease_result.get('disease', '未知')
    disease_reason = disease_result.get('reason', '')
    symptoms_str = ', '.join(structured_symptoms.get('symptoms', ['未提供']))
    duration_str = structured_symptoms.get('duration_days', '未知')
    history_str = ', '.join(structured_symptoms.get('medical_history', ['無']))
    dept_list_str = ', '.join(departments_list)
    prompt = f"""
你是B型專家，台灣資深醫師，風格積極、全面考量，避免漏診。
根據下方結構化症狀摘要與疾病推論結果，請以 JSON 格式回覆分診建議：
- urgency_level: '建議盡快就醫', '可安排門診', '非緊急'
- suggested_departments: 嚴格從 [{dept_list_str}] 選（最多3個）
- reason: 一句繁體中文說明
- disease: 疾病名稱（繁體中文）
- disease_reason: 疾病推論理由

**重要規則：僅在症狀可能代表嚴重潛在問題（例如：不明原因的劇烈頭痛、單側肢體無力、呼吸急促）時，才選擇 '建議盡快就醫'。**

症狀: {symptoms_str}
持續: {duration_str} 天
病史: {history_str}
疾病推論: {disease_name}，理由：{disease_reason}
範例：
{{
    "urgency_level": "非緊急",
    "suggested_departments": ["耳鼻喉科"],
    "reason": "症狀類似普通感冒，建議多休息並觀察症狀變化。",
    "disease": "感冒",
    "disease_reason": "症狀為流鼻水、咳嗽，最可能為感冒。"
}}
"""
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.25,
        }
    }
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        outer = response.json()
        inner_json_str = outer['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(inner_json_str)
        valid_departments = [d for d in result.get("suggested_departments", []) if d in departments_list]
        if valid_departments:
            result["suggested_departments"] = valid_departments
        else:
            result["suggested_departments"] = ["家庭醫學科"]
            result["reason"] = "AI建議的科別較特殊，已為您導向綜合性的家庭醫學科。"
        result["source"] = "Gemini-Pro-B"
        return result
    except Exception as e:
        print(f"ExpertB API失敗: {e}")
        return {"error": f"ExpertB API失敗: {str(e)}"}

def get_expert_suggestion_from_gemini_pro_A(structured_symptoms: dict, api_key: str):
    """
    ExpertA: 保守型 prompt，強調謹慎、避免過度分診。
    """
    if not api_key:
        return {"error": "未提供 Gemini API Key"}
    api_url = f"{GEMINI_PRO_API_URL}?key={api_key}"
    # 疾病推論
    disease_result = guess_disease_from_gemini_pro_A(structured_symptoms, api_key)
    disease_name = disease_result.get('disease', '未知')
    disease_reason = disease_result.get('reason', '')
    symptoms_str = ', '.join(structured_symptoms.get('symptoms', ['未提供']))
    duration_str = structured_symptoms.get('duration_days', '未知')
    history_str = ', '.join(structured_symptoms.get('medical_history', ['無']))
    dept_list_str = ', '.join(departments_list)
    prompt = f"""
你是A型專家，台灣資深醫師，風格保守、謹慎，避免過度分診。
根據下方結構化症狀摘要與疾病推論結果，請以 JSON 格式回覆分診建議：
- urgency_level: '建議盡快就醫', '可安排門診', '非緊急'
- suggested_departments: 嚴格從 [{dept_list_str}] 選（最多3個）
- reason: 一句繁體中文說明
- disease: 疾病名稱（繁體中文）
- disease_reason: 疾病推論理由

**重要規則：僅在症狀明確指向有立即生命危險的情況（例如：嚴重呼吸困難、意識不清、大量出血、劇烈胸痛）時，才選擇 '建議盡快就醫'。**

症狀: {symptoms_str}
持續: {duration_str} 天
病史: {history_str}
疾病推論: {disease_name}，理由：{disease_reason}
範例：
{{
    "urgency_level": "非緊急",
    "suggested_departments": ["家庭醫學科"],
    "reason": "症狀屬於一般不適，建議先由家庭醫學科評估。",
    "disease": "感冒",
    "disease_reason": "症狀為流鼻水、咳嗽，最可能為感冒。"
}}
"""
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1,
        }
    }
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        outer = response.json()
        inner_json_str = outer['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(inner_json_str)
        valid_departments = [d for d in result.get("suggested_departments", []) if d in departments_list]
        if valid_departments:
            result["suggested_departments"] = valid_departments
        else:
            result["suggested_departments"] = ["家庭醫學科"]
            result["reason"] = "AI建議的科別較特殊，已為您導向綜合性的家庭醫學科。"
        result["source"] = "Gemini-Pro-A"
        print("Gemini Pro parsed result:", result)
        return result
    except Exception as e:
        print(f"Gemini Pro API/解析失敗: {e}")
        return {"error": f"Gemini Pro API/解析失敗: {str(e)}"}
    # ...existing code...

def multiagent_expert_suggestion(structured_symptoms: dict, api_key: str):
    """
    同時呼叫 ExpertA/B，並融合建議。
    回傳格式：{
      "expertA": {...},
      "expertB": {...},
      "consensus": {...},
      "fusion_strategy": "consensus"/"mixed"/"fallback"
    }
    """
    # 疾病推論
    disease_A = guess_disease_from_gemini_pro_A(structured_symptoms, api_key)
    disease_B = guess_disease_from_gemini_pro_B(structured_symptoms, api_key)
    result_A = get_expert_suggestion_from_gemini_pro_A(structured_symptoms, api_key)
    result_B = get_expert_suggestion_from_gemini_pro_B(structured_symptoms, api_key)
    print("\n--- Multiagent 分診 Log ---")
    print("[ExpertA]", json.dumps(result_A, ensure_ascii=False, indent=2))
    print("[ExpertB]", json.dumps(result_B, ensure_ascii=False, indent=2))
    print("[DiseaseA]", json.dumps(disease_A, ensure_ascii=False, indent=2))
    print("[DiseaseB]", json.dumps(disease_B, ensure_ascii=False, indent=2))
    print("[Input Symptoms]", json.dumps(structured_symptoms, ensure_ascii=False, indent=2))
    consensus = {}
    fusion_strategy = ""
    if result_A.get("suggested_departments") == result_B.get("suggested_departments"):
        consensus = result_A.copy()
        fusion_strategy = "consensus"
        print("[Fusion] 兩位專家建議一致，採 consensus。")
    else:
        setA = set(result_A.get("suggested_departments", []))
        setB = set(result_B.get("suggested_departments", []))
        intersection = list(setA & setB)
        print(f"[Fusion] ExpertA 科別: {setA}")
        print(f"[Fusion] ExpertB 科別: {setB}")
        print(f"[Fusion] 交集: {intersection}")
        if intersection:
            consensus = {
                "urgency_level": max(result_A.get("urgency_level", "非緊急"), result_B.get("urgency_level", "非緊急")),
                "suggested_departments": intersection,
                "reason": "兩位專家均推薦此科別，建議優先考慮。",
                "source": "consensus",
                "diseaseA": disease_A,
                "diseaseB": disease_B
            }
            fusion_strategy = "mixed"
            print("[Fusion] 採用交集 mixed 策略。")
        else:
            consensus = {
                "urgency_level": max(result_A.get("urgency_level", "非緊急"), result_B.get("urgency_level", "非緊急")),
                "suggested_departments": list(setA | setB),
                "reason": "兩位專家建議不同科別，請依自身狀況選擇。",
                "source": "mixed",
                "diseaseA": disease_A,
                "diseaseB": disease_B
            }
            fusion_strategy = "fallback"
            print("[Fusion] 無交集，採用 union fallback 策略。")
    print(f"[Fusion Strategy] {fusion_strategy}")
    print("--- End Multiagent Log ---\n")
    return {
        "expertA": result_A,
        "expertB": result_B,
        "diseaseA": disease_A,
        "diseaseB": disease_B,
        "consensus": consensus,
        "fusion_strategy": fusion_strategy
    }


# --- Utility Function: Input Validation ---
def validate_user_input_with_gemini(question: str, answer: str, api_key: str):
    """
    [輔助工具] 呼叫 Gemini-Flash API 判斷使用者的回答是否有效，並偵測情緒。
    """
    if not api_key:
        return {"error": "未提供 Gemini API Key"}

    api_url = f"{GEMINI_FLASH_API_URL}?key={api_key}"
    
    prompt = f"""
    你是一位有耐心、且善於引導的醫療助理。你的任務是判斷使用者的回答是否有效回應了你的問題。
    **規則：**
    - 回覆必須是 JSON 格式，包含 `is_relevant` (boolean) 和 `is_refusal` (boolean)。
    - `is_relevant`: 如果回答與問題相關，或使用者雖未直接回答但提供了某些醫療資訊，應為 `true`。如果回答完全無關（例如問症狀，答天氣），應為 `false`。
    - `is_refusal`: 如果使用者明確表達不想回答、不知道、不清楚、跳過、換個問題等意圖，應為 `true`。其他情況為 `false`。
    - **重要：只要回答有描述症狀的特徵、時機、狀況（例如「咬的時候會痛」、「晚上比較痛」、「吃東西時痛」、「昨天晚上刷牙之後」），或針對是非題回答肯定語氣（如「對」、「是」），都算是相關回答 (`is_relevant`: true)。**
    - 即使使用者回答「沒有」、「不知道」，也算是相關回答，但如果他們接著說「不想回答」，那 `is_refusal` 就是 `true`。
    ---
    問題: "{question}"
    回答: "{answer}"
    你的 JSON 回應:
    """
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        outer_response = response.json()
        inner_json_str = outer_response['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(inner_json_str)
        print("Gemini Validate parsed result:", result)
        return result
    except requests.exceptions.RequestException as e:
        print(f"呼叫 Gemini 驗證 API 失敗: {e}")
        return {"is_relevant": True, "is_refusal": False}
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"解析 Gemini 回應失敗: {e}")
        print(f"原始回應: {response.text}") # type: ignore
        return {"is_relevant": True, "is_refusal": False}

def generate_followup_question(structured_data, api_key):
    """
    根據目前已收集的症狀資訊，請 Gemini 生成下一個最適合的追問問題。
    """
    # 改為統一用 prompt 生成追問，不用 if not 判斷
    api_url = f"{GEMINI_FLASH_API_URL}?key={api_key}"
    prompt = f"""
你是一位有耐心且善於引導的台灣護理師，正在進行線上問診。
目前已知病患症狀摘要如下：
- 主要症狀: {', '.join(structured_data.get('symptoms', []))}
- 持續時間: {structured_data.get('duration_days', '未知')}
- 年齡: {structured_data.get('age', '未知')}
- 性別: {structured_data.get('gender', '未知')}
- 相關病史: {', '.join(structured_data.get('medical_history', []))}
- 慢性病: {', '.join(structured_data.get('chronic_disease', []))}
- 過敏: {', '.join(structured_data.get('allergy', []))}
- 重大病史: {', '.join(structured_data.get('major_history', []))}
- 治療史: {', '.join(structured_data.get('treatment_history', []))}
請根據以上資訊，判斷還缺少哪些重要問診資料，並用自然、親切的台灣民眾日常用語，提出下一個最適合的追問問題。
**規則：**
- **使用者未提起，則無需使用稱謂，直接自然地提問即可。**
- **避免使用醫學專有名詞（例如「搏動性疼痛」、「放射痛」等），而是用大家聽得懂的說法。**
- **例如：「請問你的痛是像被敲到一樣，還是像刺刺的？」、「這種不舒服有讓你睡不好嗎？」、「除了這些症狀，還有其他讓你擔心的地方嗎？」**
如果資訊已經足夠，請回覆「資訊已足夠」。
只回覆問題本身，不要加解釋。
"""
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "text/plain",
        }
    }

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        outer_response = response.json()
        inner_text = outer_response['candidates'][0]['content']['parts'][0]['text']
        return inner_text.strip()
    except requests.exceptions.RequestException as e:
        print(f"呼叫 Gemini API 失敗: {e}")
        return "系統錯誤，請稍後再試。"
    except (KeyError, IndexError) as e:
        print(f"解析 Gemini 回應失敗: {e}")
        return "系統錯誤，請稍後再試。"
