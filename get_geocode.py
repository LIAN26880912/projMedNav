import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import re 
import requests
import json

# google geocoding API 一個月免費一萬筆資料

def clean_address(address):
    address = re.sub(r'\(.*\)|（.*）', '', address)
    address = address.split('、')[0].split(',')[0]
    return address.strip()

# geolocator = Nominatim(user_agent="MediNav_Project_App/1.0", timeout=20)

# --- 設定區 ---
GOOGLE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY = "AIzaSyC3VT6ZucjBzT-LsEn-UQGJWB7xeb_6Csg" 
input_filename = '醫療機構與人員基本資料_20231231.csv'
output_filename = 'medical_data_geocoded.csv'


def get_geocode():

    print(f"正在讀取資料: {input_filename}")
    df = pd.read_csv(input_filename)

    if 'latitude' not in df.columns:
        df['latitude'] = None
    if 'longitude' not in df.columns:
        df['longitude'] = None
        
    df_to_process = df[df['latitude'].isna() & df['longitude'].isna()].copy()
    df_to_process = df_to_process[df_to_process['縣市區名'] == '臺北市北投區']
    total_rows = len(df_to_process)
    print(f"將處理 {total_rows} 筆臺北市北投區的資料...")

    if total_rows == 0:
        print("所有醫療院所皆已有經緯度資料，無需處理。")
    else:
        print(f"將處理 {total_rows} 筆尚未有經緯度的資料...")

        for index, row in df_to_process.iterrows():
            current_index = df_to_process.index.get_loc(index)
            print(f"進度: {current_index+1}/{total_rows}", end=" | ")
            
            original_address = f"{row['地址']}"
            cleaned_address = clean_address(original_address)

            if not cleaned_address:
                print(" -> 地址為空，跳過")
                continue
            
            # 【核心修改】改用 Google Geocoding API
            params = {
                'address': cleaned_address,
                'key': API_KEY,
                'language': 'zh-TW' # 指定回傳語言為繁體中文
            }
            
            try:
                # 為了避免過於頻繁的請求，仍然保留延遲
                time.sleep(0.1) # Google API 較強健，可縮短延遲
                
                res = requests.get(GOOGLE_API_URL, params=params)
                res.raise_for_status() # 確認請求成功
                
                data = res.json() # 解析回傳的 JSON
                
                if data['status'] == 'OK':
                    location = data['results'][0]['geometry']['location']
                    lat = location['lat']
                    lng = location['lng']
                    df.at[index, 'latitude'] = lat
                    df.at[index, 'longitude'] = lng
                    print(f" -> 成功: ({lat:.4f}, {lng:.4f})  {cleaned_address}")
                else:
                    # 如果 Google 找不到地址，狀態會是 'ZERO_RESULTS'
                    df.at[index, 'longitude'] = data['status'] # 記錄失敗原因
                    print(f" -> 失敗: {data['status']}  {cleaned_address}")

            except Exception as e:
                print(f" -> 發生未知錯誤: {e}  {cleaned_address}")
                df.at[index, 'longitude'] = 'error'
                break

                
            """
            for attempt in range(3): 
                try:
                    time.sleep(1) 
                    
                    location = geolocator.geocode(cleaned_address)
                    
                    if location:
                        df.at[index, 'latitude'] = location.latitude
                        df.at[index, 'longitude'] = location.longitude
                        print(f"成功: {cleaned_address} -> ({location.latitude:.4f}, {location.longitude:.4f})")
                    else:
                        print(f"失敗: 找不到地址 {cleaned_address}")
                    
                    break # 如果成功或找不到地址，就跳出重試迴圈

                except GeocoderTimedOut:
                    print(f"超時錯誤 (第 {attempt+1} 次嘗試)... 正在等待更長時間後重試...")
                    time.sleep(5) # 如果超時，就等更久一點
                except Exception as e:
                    print(f"發生未知錯誤: {e}")
                    break # 發生其他錯誤就直接放棄
                """
        print(f"\n地理編碼完成，正在儲存至 {output_filename}")
        df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print("檔案儲存成功！")

if __name__ == "__main__":
    get_geocode()
    print("地理編碼腳本執行完畢！")