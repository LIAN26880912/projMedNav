import pandas as pd
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np

app = Flask(__name__)
CORS(app)

app.config['JSON_AS_ASCII'] = False

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



# --- API 端點 (Endpoints) ---

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

 

# --- 主程式執行區 ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
