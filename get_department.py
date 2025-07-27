import pandas as pd
import json

def extract_department_columns(input_file, output_file, start_column_index=5):
    """
    從指定的 CSV 檔案中，擷取從某個欄位索引開始的所有欄位名稱，
    並將它們儲存到一個新的檔案中。

    參數:
    input_file (str): 輸入的檔案路徑。
    output_file (str): 輸出的檔案路徑。
    start_column_index (int): 開始擷取的欄位索引值 (從 0 開始計算，F 欄位是 5)。
    """
    try:
        print(f"正在讀取檔案 '{input_file}' 的欄位結構...")
        df = pd.read_csv(input_file, encoding='utf-8-sig', nrows=0)
        df.columns = df.columns.str.strip()
        ## 這邊還沒修好        
        departments = df['科別'].str.split(',').explode().dropna().unique().tolist()

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(departments, f, ensure_ascii=False, indent=2)
            
        print(f"所有科別名稱已成功儲存至 '{output_file}'！")

    except FileNotFoundError:
        print(f"錯誤：找不到輸入的檔案 '{input_file}'。請確認檔案名稱與路徑是否正確。")
    except Exception as e:
        print(f"處理過程中發生未預期的錯誤：{e}")

# --- 腳本執行區 ---
if __name__ == "__main__":
    # 設定輸入與輸出的檔案名稱
    INPUT_PATH = 'medical_data_geocoded.csv'
    OUTPUT_PATH = 'departments_list.json'
    
    # 執行擷取函式
    extract_department_columns(INPUT_PATH, OUTPUT_PATH)