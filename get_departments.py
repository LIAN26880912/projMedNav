import pandas as pd
import json

## 這邊之後還要處理一些單位沒有寫科別為空白的
## 從csv 中抓科別進json 為list

def get_departments(input_file, output_file):
    try:
        print(f"reading '{input_file}' ...")
        df = pd.read_csv(input_file, encoding='utf-8-sig')
        departments = df['科別'].str.split(',').explode().dropna().unique().tolist()

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(departments, f, ensure_ascii=False, indent=2)
            
        print(f"successfully saved '{output_file}'！")

    except FileNotFoundError:
        print(f"error: cannot find file '{input_file}'. ")
    except Exception as e:
        print(f"unknown error {e}")

if __name__ == "__main__":
    INPUT_PATH = 'medical_data_geocoded.csv'
    OUTPUT_PATH = 'departments_list.json'
    
    get_departments(INPUT_PATH, OUTPUT_PATH)