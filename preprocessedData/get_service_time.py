import pandas as pd
import os


inputFilename = '全民健康保險特約院所固定服務時段_20250813.csv'
outputFilename = '../backend/medical_data_geocoded.csv'


def update_service_times():
    """
    讀取主要的醫療機構資料，並將健保署的服務時段資訊合併進去，
    最後直接存回原始檔案。
    """
    # --- 1. 讀取並處理服務時段資料 ---
    print(f"正在讀取服務時段檔案: {inputFilename}...")
    try:
        services_df = pd.read_csv(inputFilename, dtype={'醫事機構代碼': str})
        print("讀取成功。")
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 '{inputFilename}'。請確認檔案名稱與路徑。")
        return

    # 篩選仍在開業的院所
    services_df = services_df[services_df['開業狀況'] == 0].copy()
    print(f"篩選出 {len(services_df)} 筆仍在開業的院所。")

    # 轉換 '特約類別'
    type_map = {'1': '醫學中心', '2': '區域醫院', '3': '地區醫院', '4': '基層院所', '5': '藥局', '6': '其他'}
    services_df['特約類別_描述'] = services_df['特約類別'].map(type_map).fillna('未知')

    # 解析 '看診星期' 字串
    print("正在解析 '看診星期' 為獨立欄位...")
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    times = ['am', 'pm', 'eve']
    
    # 過濾掉格式不符的資料
    services_df = services_df[services_df['看診星期'].astype(str).str.len() == 21].copy()

    for time_idx, time_slot in enumerate(times):
        for day_idx, day in enumerate(days):
            col_name = f"{day}_{time_slot}"
            char_index = time_idx * 7 + day_idx
            services_df[col_name] = services_df['看診星期'].str[char_index].apply(lambda x: 1 if x == 'N' else 0)
    
    # 選擇最終要合併的欄位
    columns_to_merge = ['醫事機構代碼', '特約類別_描述', '看診備註'] + [f"{day}_{time}" for time in times for day in days]
    processed_services_df = services_df[columns_to_merge]
    print("服務時段資料處理完成。")

    # --- 2. 讀取主要的醫療機構資料 ---
    print(f"\n正在讀取主要的醫療機構檔案: {outputFilename}...")
    if not os.path.exists(outputFilename):
        print(f"錯誤：找不到主要的醫療機構檔案 '{outputFilename}'。")
        return
        
    main_df = pd.read_csv(outputFilename, dtype={'機構代碼': str})
    print("讀取成功。")

    # --- 3. 合併資料 ---
    # 為了合併，將 key 欄位名稱統一
    main_df.rename(columns={'機構代碼': '醫事機構代碼'}, inplace=True)

    # 在合併前，先移除 main_df 中可能已存在的舊的服務時段欄位，避免重複
    cols_to_drop = [col for col in columns_to_merge if col != '醫事機構代碼' and col in main_df.columns]
    if cols_to_drop:
        print(f"偵測到舊的服務時段欄位，將進行移除: {cols_to_drop}")
        main_df.drop(columns=cols_to_drop, inplace=True)

    # 執行左合併，將服務時段資訊附加到 main_df 後面
    print("正在合併兩個檔案...")
    merged_df = pd.merge(main_df, processed_services_df, on='醫事機構代碼', how='left')
    
    # 將欄位名稱改回來
    merged_df.rename(columns={'醫事機構代碼': '機構代碼'}, inplace=True)
    
    matched_count = merged_df['特約類別_描述'].notna().sum()
    print(f"合併完成。在 {len(main_df)} 筆資料中，成功匹配到 {matched_count} 筆服務時段資訊。")

    # --- 4. 儲存回原始檔案 ---
    print(f"\n正在將合併後的完整資料儲存回: {outputFilename}...")
    try:
        merged_df.to_csv(outputFilename, index=False, encoding='utf-8-sig')
        print("檔案儲存成功！")
    except Exception as e:
        print(f"儲存檔案時發生錯誤: {e}")


if __name__ == "__main__":

    # --- 執行處理流程 ---
    update_service_times()
    print("\n資料更新腳本執行完畢！")
