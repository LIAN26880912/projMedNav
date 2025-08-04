import pandas as pd
import json
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
import requests

app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False
GOOGLE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY = "AIzaSyC3VT6ZucjBzT-LsEn-UQGJWB7xeb_6Csg" 


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

# 【新增】在伺服器啟動時，載入症狀對照表
try:
    with open('symptom_map.json', 'r', encoding='utf-8') as f:
        symptom_map = json.load(f)
    print("成功載入症狀對照表！")
except Exception as e:
    print(f"讀取 symptom_map.json 時發生錯誤: {e}")
    symptom_map = {}

# --- API 端點 (Endpoints) ---


# 【新增】將地址轉換為經緯度的 API
@app.route('/api/geocode', methods=['GET'])
def geocode_address():
    """使用 Google Geocoding API 將地址轉換為經緯度"""
    address = request.args.get('address', '')
    if not address:
        return jsonify({'error': '請提供地址'}), 400

    params = {
        'address': address,
        'key': API_KEY,
        'language': 'zh-TW'
    }
    try:
        res = requests.get(GOOGLE_API_URL, params=params)
        res.raise_for_status()
        data = res.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return jsonify(location) # 回傳 {'lat': ..., 'lng': ...}
        else:
            return jsonify({'error': f"無法解析地址: {data['status']}"}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    """根據使用者輸入的症狀描述，推薦可能的科別"""
    if not symptom_map:
        return jsonify({"error": "症狀資料庫未載入"}), 500
        
    data = request.get_json()
    symptom_text = data.get('symptoms', '')
    if not symptom_text:
        return jsonify({'departments': []})

    # 找出所有匹配的科別
    found_departments = set() # 使用 set 來自動處理重複的科別
    for symptom_keyword, department in symptom_map.items():
        if symptom_keyword in symptom_text:
            found_departments.add(department)
    
    print(f"根據症狀: {symptom_text}，建議前往 {found_departments} 就診")

    return jsonify({'departments': list(found_departments)})



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
        clinics = (result_df[['機構名稱', '地址', '電話', 'latitude', 'longitude']]
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

# 【新增】以座標為中心的半徑搜尋 API
@app.route('/search/nearby', methods=['GET'])
def search_nearby_clinics():
    """根據使用者座標、半徑、科別，搜尋附近的診所。"""
    try:
        user_lat = float(request.args.get('lat'))
        user_lon = float(request.args.get('lon'))
        radius_km = float(request.args.get('radius', 1)) # 預設半徑 1 公里
        department_query = request.args.get('department', '')
    except (TypeError, ValueError):
        return jsonify({'error': '緯度、經度與半徑必須是有效的數字'}), 400

    if df.empty or not department_query:
        return jsonify({'error': '科別為必填欄位'}), 400

    # 1. 計算每家診所與使用者之間的距離
    distances = df.apply(
        lambda row: haversine_distance(user_lat, user_lon, row['latitude'], row['longitude']),
        axis=1
    )
    # 2. 篩選出在半徑內的診所
    nearby_df = df[distances <= radius_km].copy()
    # 3. 在半徑內的結果中，再篩選科別
    result_df = nearby_df[nearby_df['科別'].str.contains(department_query, na=False)]
    # 4. 準備回傳資料
    if not result_df.empty:
        result_df[result_df.isna()]
        clinics = (result_df[['機構名稱', '地址', '電話', 'latitude', 'longitude']]
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
