# projMedNav
## TODO
### current problem list
- 那個gemini API 一開始有時候會503, 再觀察一下

### function (list by priority)
- 新增聊天功能。可以讓使用者選擇，讓他代替兩階段流程

### optimization more 
- frontend
  - icon 還很難看，還有hover 功能
  - RWD
  - 黑暗模式
- backend
  - 緊急醫療的部分使用NLP處理
    - 急診檢傷分類標準？
  - 診所的營業時間
      - 抓開放資料
- UX
  - 科別簡化、符合一般人邏輯
    - 例如把牙醫一般科五個字縮短成牙醫之類的
  - 身心障礙牙科
  - 兒童牙科
  - 兒科診所


### expectations or considerations
- 添加緊急連絡人功能
- 語音輸入
- 台語
- 院所規模？
- 前端增加line bot
- 串接導航API
- 串接報案API
- 上線
- 定時上健保局網站拉資料
- 資料勘誤？
- 藥局
  
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