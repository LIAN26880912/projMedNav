import pandas as pd
import json
from math import radians, sin, cos, sqrt, atan2, isnan
from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
import requests
import os
from dotenv import load_dotenv

from mcp_api import (
    call_gemini_for_symptom_extraction, 
    get_expert_suggestion_from_gemini_pro,
    validate_user_input_with_gemini,
    generate_followup_question,   # <--- 補上這行
    multiagent_expert_suggestion
)


nlp = False
 
if nlp:
    from transformers import pipeline
    origins = [
        'https://projmednav.onrender.com',
        'https://mednav.sunhow123.cc',
    ]
else:
    origins = ['*']

app = Flask(__name__)
CORS(app, origins = origins)
app.config['JSON_AS_ASCII'] = False

load_dotenv()  
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
# GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"


# --- Helper Function ---
def haversine_distance(lat1, lon1, lat2, lon2):
    """計算兩個經緯度座標之間的直線距離（公里）"""
    if any(isnan(arg) for arg in [lat1, lon1, lat2, lon2]):
        return float('inf') # 如果有任何一個座標無效，回傳無限大
    R = 6371  # 地球半徑（公里）
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    a = sin(dLat/2)**2 + cos(lat1) * cos(lat2) * sin(dLon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c



# --- 資料載入 ---
try:
    df = pd.read_csv('medical_data_geocoded.csv', 
                     encoding='utf-8-sig', 
                     dtype={'機構代碼': str})
    print("成功讀取含有經緯度的醫療機構資料！")
except FileNotFoundError:
    print("錯誤：找不到 medical_data_geocoded.csv 檔案！請確認檔名與路徑。")
    df = pd.DataFrame()
except Exception as e:
    print(f"讀取 CSV 時發生未知錯誤: {e}")
    df = pd.DataFrame()

try:
    with open('departments_list.json', 'r', encoding='utf-8') as f:
        # 我們將使用這個科別列表，作為 NLP 模型的分類候選標籤
        departments_list = json.load(f)
    print("成功載入科別列表！")
except Exception as e:
    print(f"讀取 departments_list.json 時發生錯誤: {e}")
    departments_list = []

# 在伺服器啟動時，載入症狀對照表
try:
    with open('symptom_map.json', 'r', encoding='utf-8') as f:
        symptom_map = json.load(f)
    print("成功載入症狀對照表！")
except Exception as e:
    print(f"讀取 symptom_map.json 時發生錯誤: {e}")
    symptom_map = {}

try:
    with open('emergency_keywords.json', 'r', encoding='utf-8') as f:
        emergency_keywords = json.load(f)
    print("成功載入急症對照表！")
except Exception as e:
    print(f"讀取 emergency_keywords.json 時發生錯誤: {e}")
    emergency_keywords = {}





# --- API 端點 (Endpoints) ---
def get_geocode_from_google(address):
    """從 Google API 取得地址的經緯度"""
    if not address:
        return None
    params = {'address': address, 'key': GOOGLE_API_KEY, 'language': 'zh-TW'}
    try:
        res = requests.get(GEOCODE_API_URL, params=params)
        res.raise_for_status()
        data = res.json()
        if data['status'] == 'OK':
            return data['results'][0]['geometry']['location']
    except Exception as e:
        print(f"Geocoding API 發生錯誤: {e}")
    return None

@app.route('/api/geocode', methods=['GET'])
def geocode_address():
    address = request.args.get('address', '')
    location = get_geocode_from_google(address)
    if location:
        return jsonify(location)
    else:
        return jsonify({'error': '無法解析地址'}), 404


@app.route('/api/departments', methods=['GET'])
def get_all_departments():
    try:
        with open('departments_list.json', 'r', encoding='utf-8') as f:
            departments_data = json.load(f)
        return jsonify(departments_data)
    except FileNotFoundError:
        return jsonify({"error": "找不到科別列表檔案 (departments_list.json)"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/districts', methods=['GET'])
def get_all_districts():
    """讀取 admin_districts.json 並回傳。"""
    try:
        with open('admin_districts.json', 'r', encoding='utf-8') as f:
            districts_data = json.load(f)
        return jsonify(districts_data)
    except FileNotFoundError:
        return jsonify({"error": "找不到地區列表檔案 (admin_districts.json)"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 依症狀推薦科別的 API
@app.route('/api/suggest-department', methods=['POST'])
def suggest_department():
    conversation = request.json.get('symptoms')
    if not conversation:
        return jsonify({"error": "缺少症狀描述"}), 400

    # --- 步驟 1: [控制層] 呼叫 Gemini 進行對話與資訊擷取 ---
    # 為了簡化，我們先假設一次對話就能完成。
    # 完整的實作需要處理 is_info_complete 為 false 的情況，進行多輪對話。
    structured_data = call_gemini_for_symptom_extraction(conversation, GOOGLE_API_KEY)
    
    if 'error' in structured_data:
        return jsonify(structured_data), 500

    # --- 步驟 2: [專家層] 呼叫 Hugging Face 模型進行專業判斷 ---
    expert_suggestion = get_expert_suggestion_from_gemini_pro(structured_data, GOOGLE_API_KEY)

    if 'error' in expert_suggestion:
        return jsonify(expert_suggestion), 500

    # --- 步驟 3: 回傳最終結果 ---
    # 將專家建議與結構化資訊合併，方便前端使用或未來除錯
    final_result = {
        "source": "MCP_2.0",
        "suggestion": expert_suggestion,
        "extracted_data": structured_data
    }

    # expert_suggestion["suggested_departments"] 是陣列
    # 搜尋所有科別
    clinics = []
    for dept in expert_suggestion.get("suggested_departments", []):
        clinics += search_clinics_by_department(dept)

    return jsonify(final_result) 

@app.route('/api/validate-input', methods=['POST'])
def validate_input():
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    if not question or not answer:
        return jsonify({"error": "缺少問題或回答"}), 400
    
    validation_result = validate_user_input_with_gemini(question, answer, GOOGLE_API_KEY)
    return jsonify(validation_result)     


def get_return_columns():
    """定義所有需要回傳給前端的欄位"""
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    times = ['am', 'pm', 'eve']
    service_time_cols = [f"{day}_{time}" for time in times for day in days]
    base_cols = ['機構名稱', '地址', '縣市區名', '電話', 'latitude', 'longitude', '特約類別_描述']
    return base_cols + service_time_cols

@app.route('/search', methods=['GET'])
def search_clinic():
    department_query = request.args.get('department', '')
    city_query = request.args.get('city', '')
    district_query = request.args.get('district', '')
    if df.empty or not department_query or not city_query:
        # 即使 department_query 有值，也可能在下一步變成空列表，所以在此不急著返回錯誤
        pass # 讓後續邏輯處理

    # --- 新增的科別處理邏輯 ---
    # 1. 將字串用逗號拆分成列表，並移除多餘的空白
    department_list = [dept.strip() for dept in department_query.split(',') if dept.strip()]
    if not department_list:
        return jsonify([{'error': '科別為必填欄位'}]), 400
    # 2. 用正規表示式的 "OR" (|) 連接所有科別
    department_regex = '|'.join(department_list)
    # --- 結束 ---

    full_address_prefix = city_query + district_query
    
    # 3. 在查詢中使用新的 regex 變數
    result_df =  df[df['縣市區名'].str.startswith(full_address_prefix, na=False) & 
                    df['科別'].str.contains(department_regex, na=False, regex=True)].copy()


    '''
    if not result_df.empty:
        result_df = result_df.dropna(subset=['latitude', 'longitude'])
    '''
    
    # 取得行政區中心點來排序
    center_location = get_geocode_from_google(full_address_prefix)
    if center_location:
        center_lat, center_lon = center_location['lat'], center_location['lng']
        result_df['distance'] = result_df.apply(
            lambda row: haversine_distance(center_lat, center_lon, row['latitude'], row['longitude']),
            axis=1
        )
        result_df.sort_values(by='distance', inplace=True)


    # 選擇需要的欄位並轉換為字典
    cols_to_return = get_return_columns()
    # 確保所有需要的欄位都存在
    for col in cols_to_return:
        if col not in result_df.columns:
            result_df[col] = np.nan

    result_df = result_df.replace('', np.nan).fillna('未提供')
    
    '''
    if not result_df.empty:
        result_df[result_df.isna()]
        clinics = (result_df[['機構名稱', '地址', '縣市區名', '電話', 'latitude', 'longitude']]
            .replace({
                '地址': {np.nan: '未提供地址', '': '未提供地址'}, 
                '電話': {np.nan: '未提供電話', '': '未提供電話'}})
            .to_dict('records')
        )

    else:
        clinics = []
    '''

    clinics = result_df[cols_to_return].to_dict('records')

    print(f"查詢: {full_address_prefix} - {department_query}，找到 {len(clinics)} 筆資料。")
   
    return jsonify(clinics)

@app.route('/search/nearby', methods=['GET'])
def search_nearby_clinics():
    try:
        user_lat = float(request.args.get('lat'))
        user_lon = float(request.args.get('lon'))
        radius_km = float(request.args.get('radius', 1)) 
        department_query = request.args.get('department', '')
    except (TypeError, ValueError):
        return jsonify([{'error': '緯度、經度與半徑必須是有效的數字'}]), 400

    # --- 新增的科別處理邏輯 ---
    if df.empty:
        return jsonify([]), 200 # 如果資料是空的，直接回傳空列表

    department_list = [dept.strip() for dept in department_query.split(',') if dept.strip()]
    if not department_list:
        return jsonify([{'error': '科別為必填欄位'}]), 400
    department_regex = '|'.join(department_list)
    # --- 結束 ---

    distances = df.apply(
        lambda row: haversine_distance(user_lat, user_lon, row['latitude'], row['longitude']),
        axis=1
    )

    # 在查詢中使用新的 regex 變數
    result_df = df[(distances <= radius_km) & 
                   (df['科別'].str.contains(department_regex, na=False, regex=True))].copy()


    # 依距離排序
    result_df['distance'] = distances[result_df.index]
    result_df.sort_values(by='distance', inplace=True)

    # 選擇需要的欄位並轉換為字典
    cols_to_return = get_return_columns() + ['distance']
    for col in cols_to_return:
        if col not in result_df.columns:
            result_df[col] = np.nan
    
    result_df = result_df.replace('', np.nan).fillna('未提供')

    """
    if not result_df.empty:
        result_df[result_df.isna()]
        clinics = (result_df[['機構名稱', '地址', '縣市區名', '電話', 'latitude', 'longitude']]
            .head(100)
            .replace({
                '地址': {np.nan: '未提供地址', '': '未提供地址'}, 
                '電話': {np.nan: '未提供電話', '': '未提供電話'}})
            .to_dict('records')
        )
    
    else:
        clinics = []
    """

    clinics = result_df[cols_to_return].to_dict('records')
        
    print(f"附近查詢: ({user_lat}, {user_lon}) 半徑 {radius_km}km - {department_query}，找到 {len(clinics)} 筆資料。")
    return jsonify(clinics)

@app.route('/api/dialogue', methods=['POST'])
def dialogue_manager():
    conversation_history = request.json.get('conversation_history', '')
    if not conversation_history:
        return jsonify({"error": "缺少對話紀錄"}), 400

    # --- 相關性判斷邏輯 (維持不變) ---
    lines = conversation_history.strip().split('\n')
    last_user_line = next((line for line in reversed(lines) if line.startswith("使用者:")), None)
    last_ai_line = next((line for line in reversed(lines) if line.startswith("AI:")), None)

    def is_user_refusal(answer):
        refusal_keywords = ["沒有", "不知道", "不清楚", "不想回答", "拒絕回答", "略過", "跳過"]
        return any(k in answer for k in refusal_keywords)

    if last_user_line and last_ai_line:
        last_answer = last_user_line.replace("使用者: ", "").strip()
        last_question = last_ai_line.replace("AI: ", "").strip()
        if not is_user_refusal(last_answer):
            validation = validate_user_input_with_gemini(last_question, last_answer, GOOGLE_API_KEY)
            if not validation.get("is_relevant", True):
                return jsonify({
                    "action": "ask_more",
                    "next_question": validation.get("feedback", "抱歉，請針對問題提供資訊喔。"),
                    "extracted_data": {}
                })
    # --- 相關性判斷結束 ---

    # 步驟 1: 症狀抽取
    structured_data = call_gemini_for_symptom_extraction(conversation_history, GOOGLE_API_KEY)
    if 'error' in structured_data:
        return jsonify(structured_data), 500
    
    # --- 【主要修改】步驟 2: 呼叫 Multi-agent 進行分診建議 ---
    multiagent_result = multiagent_expert_suggestion(structured_data, GOOGLE_API_KEY)
    # 使用融合後的共識 (consensus) 作為主要建議
    expert_suggestion = multiagent_result.get("consensus", {})

    if not expert_suggestion:
         # 如果連共識都沒有，可能 multi-agent 執行失敗
        return jsonify({"error": "Multi-agent 專家系統分析失敗"}), 500

    # 步驟 3: 根據 Multi-agent 結果判斷流程
    # 緊急判斷：直接給急診指引，結束對話
    if expert_suggestion.get('urgency_level') == '建議盡快就醫':
        return jsonify({
            "action": "emergency",
            "suggestion": expert_suggestion, # 回傳共識結果
            "multiagent_full_result": multiagent_result, # 可選擇性回傳完整報告
            "extracted_data": structured_data
        })

    # 非緊急：如果個人資訊不完整，繼續追問
    if not structured_data.get('is_info_complete', True):
        next_question = generate_followup_question(structured_data, GOOGLE_API_KEY)
        return jsonify({
            "action": "ask_more",
            "next_question": next_question,
            "extracted_data": structured_data
        })

    # 非緊急且資訊完整，給分診建議
    return jsonify({
        "action": "suggest",
        "suggestion": expert_suggestion, # 回傳共識結果
        "multiagent_full_result": multiagent_result, # 可選擇性回傳完整報告
        "extracted_data": structured_data
    })



def search_clinics_by_department(department):
    """根據科別搜尋所有診所（不分地區）"""
    if df.empty or not department:
        return []
    result_df = df[df['科別'].str.contains(department, na=False)].copy()
    cols_to_return = get_return_columns()
    for col in cols_to_return:
        if col not in result_df.columns:
            result_df[col] = np.nan
    result_df = result_df.replace('', np.nan).fillna('未提供')
    return result_df[cols_to_return].to_dict('records')


# --- Multiagent 分診 API 端點 ---
@app.route('/api/suggest-department-multiagent', methods=['POST'])
def suggest_department_multiagent():
    conversation = request.json.get('symptoms')
    if not conversation:
        return jsonify({"error": "缺少症狀描述"}), 400

    # 步驟 1: 症狀抽取
    structured_data = call_gemini_for_symptom_extraction(conversation, GOOGLE_API_KEY)
    if 'error' in structured_data:
        return jsonify(structured_data), 500

    # 步驟 2: multi-agent 分診建議
    multiagent_result = multiagent_expert_suggestion(structured_data, GOOGLE_API_KEY)
    print("\n=== API Log: /api/suggest-department-multiagent ===")
    print("[Symptoms]", json.dumps(structured_data, ensure_ascii=False, indent=2))
    print("[Multiagent Result]", json.dumps(multiagent_result, ensure_ascii=False, indent=2))
    print("===============================================\n")
    # 步驟 3: 回傳
    final_result = {
        "source": "MCP_2.0_multiagent",
        "multiagent_suggestion": multiagent_result,
        "extracted_data": structured_data,
        "diseaseA": multiagent_result.get("diseaseA", {}),
        "diseaseB": multiagent_result.get("diseaseB", {})
    }
    clinics = []
    consensus_depts = multiagent_result.get("consensus", {}).get("suggested_departments", [])
    for dept in consensus_depts:
        clinics += search_clinics_by_department(dept)
    final_result["clinics"] = clinics
    return jsonify(final_result)

# --- 主程式執行區 ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)