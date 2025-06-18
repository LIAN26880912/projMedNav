import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 【核心修正】更新 MAP，使其 value 與 CSV 檔中的欄位名稱完全一致
DEPARTMENT_MAP = {
    "牙科": "C牙醫師",
    "牙科一般科": "C牙醫師", # 這裡我們假設都對應到專科醫師數
    "家醫科": "家醫科醫師",
    "內科": "內科醫師",
    "外科": "外科醫師",
    "兒科": "兒科醫師",
    "眼科": "眼科醫師",
    "皮膚科": "皮膚科醫師",
    "耳鼻喉科": "耳鼻喉科醫師"
}

try:
    # 【修正】加入 dtype={'機構代碼': str} 來解決 DtypeWarning
    # 這會告訴 Pandas 將'機構代碼'欄位統一當作文字處理
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


@app.route('/search', methods=['GET'])
def search_clinic():
    department_query = request.args.get('department', '')
    city_query = request.args.get('city', '')
    
    if df.empty or not department_query or not city_query:
        return jsonify({'error': '資料不完整或伺服器資料讀取失敗'}), 400
    
    db_column_name = DEPARTMENT_MAP.get(department_query, department_query)

    result_df = df[df['地址'].str.startswith(city_query, na=False)].copy()
    
    if db_column_name in result_df.columns:
        result_df[db_column_name] = pd.to_numeric(result_df[db_column_name], errors='coerce').fillna(0)
        result_df = result_df[result_df[db_column_name] > 0]
    else:
        print(f"警告：找不到名為 '{department_query}' (對應 '{db_column_name}') 的科別欄位。")
        result_df = pd.DataFrame()

    if not result_df.empty:
        result_df = result_df.dropna(subset=['latitude', 'longitude'])
    
    # 【修正】回傳的欄位名稱也必須與 CSV 檔完全一致 ('機構地址', '機構電話')
    # 確保 result_df 不是空的，才進行欄位選取
    if not result_df.empty:
        clinics = result_df[['機構名稱', '地址', 'latitude', 'longitude']].head(20).to_dict('records')
    else:
        clinics = [] # 如果 result_df 是空的，就回傳一個空列表
    
    print(f"查詢: {city_query} - {department_query} (對應到 {db_column_name})，找到 {len(clinics)} 筆資料。")
    
    return jsonify(clinics)

if __name__ == '__main__':
    app.run(debug=True)