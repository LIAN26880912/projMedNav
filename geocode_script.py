import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import re # 匯入正規表示式函式庫，用於文字清洗

# 1.【升級】建立一個地址清洗函式
def clean_address(address):
    # 去除括號及其中的內容 (包括全形和半形括號)
    address = re.sub(r'\(.*\)|（.*）', '', address)
    # 如果地址中有多個門牌號 (用頓號、逗號分隔)，只取第一個
    address = address.split('、')[0].split(',')[0]
    # 去除頭尾多餘的空格
    return address.strip()

# 2.【升級】初始化地理編碼器時，增加 timeout 時間
geolocator = Nominatim(user_agent="MediNav_Project_App/1.0", timeout=20)

# 讀取你的原始 CSV 檔案
input_filename = '醫療機構與人員基本資料_20231231.csv' # 請確認你的檔名
output_filename = 'medical_data_geocoded.csv'

print(f"正在讀取資料: {input_filename}")
df = pd.read_csv(input_filename)

# 建立新的欄位來存放經緯度
if 'latitude' not in df.columns:
    df['latitude'] = None
if 'longitude' not in df.columns:
    df['longitude'] = None

# 先處理臺北市北投區的資料作為範例
df_to_process = df[df['縣市區名'] == '臺北市北投區'].copy()
total_rows = len(df_to_process)
print(f"將處理 {total_rows} 筆臺北市北投區的資料...")

# 遍歷 DataFrame 中的每一行來進行地址轉換
for index, row in df_to_process.iterrows():
    # 3.【升級】顯示處理進度
    print(f"進度: {index+1}/{total_rows}", end=" | ")
    
    # 組合並清洗地址
    original_address = f"{row['機構名稱']}"
    cleaned_address = clean_address(original_address)
    
    # 如果該行已經有經緯度資料，則跳過
    if pd.notna(row.get('latitude')):
        print(f"已存在，跳過: {cleaned_address}")
        continue

    # 4.【升級】加入重試機制
    for attempt in range(3): # 最多重試 3 次
        try:
            time.sleep(1) # 每次請求之間固定延遲 1 秒
            
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

# 將包含新經緯度的完整 DataFrame 儲存
print(f"\n地理編碼完成，正在儲存至 {output_filename}")
# 我們儲存原始的 df，而不是 df_to_process，這樣才會包含所有縣市的資料
df.to_csv(output_filename, index=False, encoding='utf-8-sig')
print("檔案儲存成功！")