import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 업로드 폴더 없으면 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        filename = secure_filename(file.filename)
        if filename:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
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
    port = int(os.environ.get('PORT', 5000))  # Render가 지정한 포트
    app.run(host='0.0.0.0', port=port)
