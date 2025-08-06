import pandas as pd
import json
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
import requests
import os
from dotenv import load_dotenv
# from transformers import pipeline

from gemini_api import call_gemini_for_suggestion

app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

load_dotenv()  
API_KEY = os.getenv("API_KEY")
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
# GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"


# --- Helper Function ---
def haversine_distance(lat1, lon1, lat2, lon2):
    """計算兩個經緯度座標之間的直線距離（公里）"""
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

# 【新增】在伺服器啟動時，載入症狀對照表
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



try:
    """
    print("正在載入本地 NLP 模型 (第一次啟動會需要較長時間下載)...")
    # 使用 "zero-shot-classification" 任務，它可以在沒有特別訓練的情況下，對文本進行分類
    # 我們選用一個表現優異的中文 RoBERTa 模型
    nlp_classifier = pipeline("zero-shot-classification", model="hfl/chinese-roberta-wwm-ext")
    print("NLP 模型載入成功！")
    """
    nlp_classifier = None
    print("本地 NLP 模型先停用，不然部屬上去的RAM 會爆炸。將依賴關鍵字與 Gemini API。")

except Exception as e:
    print(f"載入 NLP 模型時發生錯誤: {e}")
    nlp_classifier = None

# --- API 端點 (Endpoints) ---
@app.route('/api/geocode', methods=['GET'])
def geocode_address():
    """使用 Google Geocoding API 將地址轉換為經緯度"""
    address = request.args.get('address', '')
    if not address:
        return jsonify({'error': '請提供地址'}), 400
    params = { 'address': address, 'key': API_KEY, 'language': 'zh-TW'}
    try:
        res = requests.get(GEOCODE_API_URL, params=params)
        res.raise_for_status()
        data = res.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return jsonify(location) # 回傳 {'lat': ..., 'lng': ...}
        else:
            return jsonify({'error': f"無法解析地址: {data['status']}"}), 404
    except Exception as e:
        # 在後端伺服器控制台印出詳細錯誤，方便自己除錯
        print(f"Geocoding API 發生錯誤: {e}") 
        # 【修正】回傳給前端一個通用的、安全的訊息
        return jsonify({'error': '地理編碼服務暫時無法使用，請稍後再試。'}), 500
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

# 【新增】依症狀推薦科別的 API
@app.route('/api/suggest-department', methods=['POST'])
def suggest_department():
    data = request.get_json()
    symptom_text = data.get('symptoms', '')
    if not symptom_text:
        return jsonify({'departments': []})

    # --- 【核心修改】層級 0: 緊急狀況判斷 ---
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
        print(f"Symptom Map 高優先度分析結果: {list(found_departments)}")
        return jsonify({'departments': list(found_departments)})

    # --- 層級 2: 如果關鍵字無匹配，則使用本地 NLP 模型 ---
    if not nlp_classifier or not departments_list:
        return jsonify({"error": "關鍵字無匹配，且 NLP 服務未準備就緒"}), 500


    localNLPuse = False
    """
    print("關鍵字無匹配，轉交本地 NLP 模型進行分析...")
    result = nlp_classifier(symptom_text, departments_list, multi_label=True)
    
    top_label = result['labels'][0]
    top_score = result['scores'][0]
    print(f"本地 NLP 分析結果: {top_label} (信心分數: {top_score:.2f})")

    # --- 層級 3: 如果本地模型信心度不足，則請求 Gemini 專家分析 ---
    CONFIDENCE_THRESHOLD = 0.9  # 設定信心度門檻
    
    if top_score >= CONFIDENCE_THRESHOLD:
        return jsonify({'departments': [top_label]})
    """
    if localNLPuse: 
        print("local NLP use")
    else:
        gemini_result = call_gemini_for_suggestion(symptom_text, departments_list, API_KEY)
        return jsonify({'departments': gemini_result})      



@app.route('/search', methods=['GET'])
def search_clinic():
    department_query = request.args.get('department', '')
    city_query = request.args.get('city', '')
    district_query = request.args.get('district', '')
    if df.empty or not department_query or not city_query:
        return jsonify({'error': '資料不完整或伺服器資料讀取失敗'}), 400
    full_address_prefix = city_query + district_query

    result_df = df[df['縣市區名'].str.startswith(full_address_prefix, na=False)].copy()
    result_df = result_df[result_df['科別'].str.contains(department_query, na=False)]

    if not result_df.empty:
        result_df = result_df.dropna(subset=['latitude', 'longitude'])
    
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
        return jsonify({'error': '緯度、經度與半徑必須是有效的數字'}), 400

    if df.empty or not department_query:
        return jsonify({'error': '科別為必填欄位'}), 400

    distances = df.apply(
        lambda row: haversine_distance(user_lat, user_lon, row['latitude'], row['longitude']),
        axis=1
    )
    nearby_df = df[distances <= radius_km].copy()
    result_df = nearby_df[nearby_df['科別'].str.contains(department_query, na=False)]
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
        
    print(f"附近查詢: ({user_lat}, {user_lon}) 半徑 {radius_km}km - {department_query}，找到 {len(clinics)} 筆資料。")
    return jsonify(clinics)

 

# --- 主程式執行區 ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
