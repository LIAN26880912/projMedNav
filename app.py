import pandas as pd
import json
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- 資料載入 ---
try:
    # 載入診所主資料，並指定'機構代碼'為字串以避免DtypeWarning
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

# 【新增】建立一個專門提供科別列表的 API
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


# 【新增】建立一個專門提供縣市與鄉鎮市區資料的 API
@app.route('/api/districts', methods=['GET'])
def get_all_districts():
    """讀取 admin_districts.json 並回傳。"""
    try:
        # 您上傳的檔案名稱是 admin_districts.json
        with open('admin_districts.json', 'r', encoding='utf-8') as f:
            districts_data = json.load(f)
        return jsonify(districts_data)
    except FileNotFoundError:
        return jsonify({"error": "找不到地區列表檔案 (admin_districts.json)"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 【修正】搜尋診所的 API，採用新的「長表格」搜尋邏輯
@app.route('/search', methods=['GET'])
def search_clinic():
    # 根據前端傳來的縣市和科別，搜尋符合條件的診所。
    # 【修正】將 'return' 改為 'request'
    department_query = request.args.get('department', '')
    city_query = request.args.get('city', '')
    district_query = request.args.get('district', '')
    
    if df.empty or not department_query or not city_query:
        return jsonify({'error': '資料不完整或伺服器資料讀取失敗'}), 400
    
    full_address_prefix = city_query + district_query

    # --- 【核心邏輯修正】改為在「科別」欄位中進行文字搜尋 ---
    
    # 1. 先依據地址前綴篩選縣市
    result_df = df[df['地址'].str.startswith(city_query, na=False)].copy()
    
    # 2. 在篩選出的結果中，進一步尋找 '科別' 欄位包含指定科別關鍵字的資料
    #    使用 .str.contains() 進行模糊比對，na=False 避免空值錯誤
    result_df = result_df[result_df['科別'].str.contains(department_query, na=False)]

    # 3. 過濾掉沒有經緯度的資料
    if not result_df.empty:
        result_df = result_df.dropna(subset=['latitude', 'longitude'])
    
    # 4. 準備回傳的資料
    if not result_df.empty:
        # 【修正】確保回傳的欄位名稱與 CSV 檔一致，並加入'電話'欄位
        clinics = result_df[['機構名稱', '地址', '電話', 'latitude', 'longitude']].head(20).to_dict('records')
    else:
        clinics = []
    
    print(f"查詢: {city_query} - {department_query}，找到 {len(clinics)} 筆資料。")
    
    return jsonify(clinics)

 

# --- 主程式執行區 ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
