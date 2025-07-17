import os
import re
from flask import Flask, render_template, request, jsonify
from urllib.parse import quote

app = Flask(__name__)

# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ⚠️ 파일명에서 위험한 문자는 제거하되 한글, 영문, 숫자, 일부 특수문자만 허용
def sanitize_filename(filename):
    # 폴더 경로 제거 + 확장자 분리
    name, ext = os.path.splitext(os.path.basename(filename))
    # 한글, 영문, 숫자, 일부 기호만 허용
    name = re.sub(r'[^가-힣a-zA-Z0-9_\-\(\)\[\]\s]', '', name)
    return f"{name}{ext}"

# index 페이지
@app.route('/')
def index():
    return render_template('index.html')

# 파일 업로드 처리
@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist('files[]')
    saved_files = []

    for file in uploaded_files:
        if file.filename:
            filename = sanitize_filename(file.filename)  # 한글 포함 안전 필터링
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            saved_files.append(filename)

    return jsonify({'success': True, 'files': saved_files})

# 저장된 파일 목록 반환
@app.route('/files', methods=['GET'])
def list_files():
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        return jsonify({'files': files})
    except FileNotFoundError:
        return jsonify({'files': []})

# Render 배포용 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
