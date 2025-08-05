# projMedNav
## TODO
### current problem list
nil

### function (list by priority)
- 輕重緩急判斷
- 推薦複數科別
- 聊天功能

### optimization more 
- frontend
  - icon 還很難看，還有hover 功能
  - RWD
  - 整個使用流程還可以直覺一點
  - 黑暗模式
- backend
  - 診所的營業時間
  - 急診

### expectations or considerations
- 語音輸入
- 台語
- 院所規模？
- 前端增加line bot
- 串接導航API
- 串接報案API
- 上線

### notification (to myself) 
- API key 上線前一定要拿掉
  

  
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