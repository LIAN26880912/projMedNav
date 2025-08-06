# projMedNav
## TODO
### current problem list
- 那個gemini API 一開始有時候會503, 再觀察一下

### function (list by priority)
- 營業時間
  - 考量要怎麼用政府的公開資料，以及從google map 取來的資料
- 排序功能
  - 有無營業
  - 距離遠近
- 新增聊天功能。可以讓使用者選擇，讓他代替兩階段流程

### optimization more 
- frontend
  - RWD
  - 黑暗模式
- backend
  - 緊急醫療的部分使用NLP處理
    - 急診檢傷分類標準？
  - 診所的營業時間
      - 抓開放資料
- UX
  - 科別調整
    - 符合一般人邏輯
    例如把牙醫一般科五個字縮短成牙醫之類的
    - 其他沒寫到的牙科科別
      - 身心障礙牙科
      - 兒童牙科
      - 兒科診所


### expectations or considerations
- 添加緊急連絡人功能（登入功能）
- 語音輸入、聊天、純聊天無障礙模式？
- 台語
- 院所規模？
- 前端增加line bot
- 語音撥號報案（緊急案件only, 參考apple watch）
- 上線
- 定時上健保局網站拉資料
- 資料勘誤？
- 藥局
- 有無健保、院所等級（費用）
- 串院所的看診、預約掛號系統？
  
---
# run
```
# server:
python app.py

# front:
# open index.html
```
## current function
- 根據要找的科別找到指定地點區域附近的醫療院所
## limitation so far
- geocode 先手動更新自己要用的縣市就好