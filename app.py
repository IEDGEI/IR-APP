import os
import re
from flask import Flask, render_template, request, jsonify
from urllib.parse import quote
import pandas as pd
import fitz  # PyMuPDF for PDF
import docx  # python-docx for DOCX

app = Flask(__name__)

# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 한글+보안 허용 파일명 필터링 함수
def sanitize_filename(filename):
    name, ext = os.path.splitext(os.path.basename(filename))
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
            filename = sanitize_filename(file.filename)
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

# 파일 제목 또는 내용에서 키워드 검색
@app.route('/search', methods=['POST'])
def search_files():
    keyword = request.json.get('keyword', '').strip()
    if not keyword:
        return jsonify({'matches': []})

    results = []

    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        ext = os.path.splitext(filename)[-1].lower()

        match_title = keyword in filename
        match_content = False
        content = ''

        try:
            if ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
                content = df.to_string()
            elif ext == '.xlsx':
                df = pd.read_excel(file_path)
                content = df.to_string()
            elif ext == '.pdf':
                doc = fitz.open(file_path)
                content = '\n'.join([page.get_text() for page in doc])
            elif ext == '.docx':
                doc = docx.Document(file_path)
                content = '\n'.join([p.text for p in doc.paragraphs])
            # (.hwp 는 별도 처리 필요)
            match_content = keyword in content

        except Exception as e:
            print(f"[ERROR reading {filename}]: {e}")

        results.append({
            'filename': filename,
            'matched': match_title or match_content
        })

    # 일치한 파일 먼저 정렬
    results.sort(key=lambda x: not x['matched'])

    return jsonify({'matches': results})

# Render 배포용 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
