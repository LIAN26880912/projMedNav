# projMedNav
## Deployment
<https://mednav.sunhow123.cc>


## TODO
### current problem list
- 急診的服務時間要再加上
- 之前有些院所的時間不會顯示，要再確認一下
- 部屬上去之後的列表css 好像掛了，再檢查一下
- 分析錯誤的時候有一個重新開始按鈕
- 訊息的顯示可以改用logging

### function (list by priority)
- 新增聊天功能。可以讓使用者選擇，讓他代替兩階段流程

### optimization more 
- frontend
  - 營業的時間考慮看看要不要抓google map
  - （感覺這個應該算微調）或許在還沒點下去前，可以有很多簡易popup, 點下去後才是大popup
- backend
  - 緊急醫療的部分使用NLP處理
    - 先用prompt engeering 讓gemini 處理
    - 考慮使用openmed
- 權利義務相關
  - 宣讀（未有診斷功能）
  - 院所營業時間為健保局資料，確切要問院所、加上資料最近更新時間
  - 

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

### REFs
- [OpenMed 醫療NLP model](https://www.threads.com/@sliven0722/post/DMmNhZggTuO?xmt=AQF0XV3glCwnjPmjg_OjD-HJkCbXZCHNf3BhfqnSXRrq7Q)
- 緊急避難地圖3.0
  - [介紹影片](https://www.facebook.com/watch/?v=1237349654221012&rdid=qxOLGHNKaTsAJ71G)
  - [地圖本體](https://taiwan-emergency-shelter-finder.vercel.app/)
  
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