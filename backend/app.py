import pandas as pd
import json
from math import radians, sin, cos, sqrt, atan2, isnan
from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
import requests
import os
from dotenv import load_dotenv

from gemini_api import call_gemini_for_suggestion, call_gemini_for_validation

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
API_KEY = os.getenv("API_KEY")
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
    params = {'address': address, 'key': API_KEY, 'language': 'zh-TW'}
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


@app.route('/api/validate-answer', methods=['POST'])
def validate_answer():
    data = request.get_json()
    question = data.get('question')
    answer = data.get('answer')
    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400

    # 呼叫 gemini_api 中的新函式
    validation_result = call_gemini_for_validation(question, answer, API_KEY)
    return jsonify(validation_result)


# 依症狀推薦科別的 API
@app.route('/api/suggest-department', methods=['POST'])
def suggest_department():
    data = request.get_json()
    symptom_text = data.get('symptoms', '')
    if not symptom_text:
        return jsonify({'departments': []})

    # --- 層級 0: 緊急狀況判斷 ---
    for keyword in emergency_keywords:
        if keyword in symptom_text:
            print(f"偵測到緊急關鍵字: {keyword}")
            # 回傳一個特殊的緊急狀態物件
            return jsonify({"emergency": True, "matched_keyword": keyword})

    # --- 層級 1: 優先使用 symptom_map.json 進行關鍵字匹配 ---
    found_departments = set()
    if symptom_map:
        for symptom_keyword, department in symptom_map.items():
            if symptom_keyword in symptom_text:
                found_departments.add(department)
    if found_departments:
        # 如果關鍵字匹配到，我們也用 Gemini 的格式回傳，方便前端統一處理
        print(f"Symptom Map 高優先度分析結果: {list(found_departments)[0]}")
        return jsonify({
            "department": list(found_departments)[0],
            "urgency_level": "可安排門診",
            "recommendation_reason": "根據症狀關鍵字匹配"
        })
    print("關鍵字無匹配，轉交其他模型進行分析...")

    # --- 層級 2: 如果關鍵字無匹配，且非雲端部屬模式，則使用本地 NLP 模型 ---


    # --- 層級 3: 如果本地模型信心度不足，則請求 Gemini 專家分析 ---
    print("本地 NLP 模型信心度不足，或未使用本地 NLP ，請求 Gemini API 進行分析...")
    gemini_result = call_gemini_for_suggestion(symptom_text, departments_list, API_KEY)
    return jsonify(gemini_result)      


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
        return jsonify([{'error': '緯度、經度與半徑必須是有效的數字'}]), 400

    full_address_prefix = city_query + district_query
    result_df =  df[df['縣市區名'].str.startswith(full_address_prefix, na=False) & 
                    df['科別'].str.contains(department_query, na=False)].copy()

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

    if df.empty or not department_query:
        return jsonify([{'error': '科別為必填欄位'}]), 400

    distances = df.apply(
        lambda row: haversine_distance(user_lat, user_lon, row['latitude'], row['longitude']),
        axis=1
    )

    result_df = df[(distances <= radius_km) & 
                   (df['科別'].str.contains(department_query, na=False))].copy()

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

 

# --- 主程式執行區 ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)