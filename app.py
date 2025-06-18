from flask import Flask, jsonify, request

app = Flask(__name__)

# 這就是你的第一個 API 端點 (API Endpoint)
@app.route('/ask', methods=['GET'])
def ask_symptom():
    # 接收前端傳來的問題，例如 '牙痛'
    symptom = request.args.get('symptom', '未知症狀')

    # 【極度簡化版邏輯】先寫死規則
    if '牙' in symptom or '牙齒' in symptom:
        suggestion = '牙科'
    elif '皮膚' in symptom or '疹子' in symptom:
        suggestion = '皮膚科'
    else:
        suggestion = '家醫科'

    # 回傳一個 JSON 格式的資料
    return jsonify({
        'input_symptom': symptom,
        'suggested_department': suggestion
    })

if __name__ == '__main__':
    app.run(debug=True) # debug=True 讓你可以修改後自動重啟