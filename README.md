# projMedNav
## TODO
### current problem list
- 那個gemini API 挺不穩的，常常會error 503

### function (list by priority)
- 推薦複數科別
  - 包含科別重新調整
    - 例如把牙醫一般科五個字縮短成牙醫之類的
- 聊天功能

### optimization more 
- frontend
  - icon 還很難看，還有hover 功能
  - RWD
  - 整個使用流程還可以直覺一點
  - 黑暗模式
- backend
  - 緊急醫療的部分使用NLP處理
    - 急診檢傷分類標準？
  - 診所的營業時間
      - 抓開放資料
  - 


### expectations or considerations
- 語音輸入
- 台語
- 院所規模？
- 前端增加line bot
- 串接導航API
- 串接報案API
- 上線
  
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