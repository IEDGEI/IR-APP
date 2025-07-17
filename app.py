import os
import re
from flask import Flask, render_template, request, jsonify, send_file
from urllib.parse import quote
import pandas as pd
import fitz  # PyMuPDF for PDF
import docx  # python-docx for DOCX
import io    # 엑셀 병합 결과를 메모리에 저장

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

# 🔥 파일 삭제 처리
@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': '파일명이 누락됨'})

    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '파일이 존재하지 않음'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 🔍 파일 제목 또는 내용에서 키워드 검색
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
            match_content = keyword in content

        except Exception as e:
            print(f"[ERROR reading {filename}]: {e}")

        results.append({
            'filename': filename,
            'matched': match_title or match_content
        })

    results.sort(key=lambda x: not x['matched'])

    return jsonify({'matches': results})

# ✅ 병합된 엑셀 생성 API (업로드된 파일 중 선택된 2개 사용)
@app.route('/merge_custom_horizontal_named', methods=['POST'])
def merge_custom_horizontal_named():
    try:
        data = request.get_json()
        file1 = sanitize_filename(data.get('file1'))
        file2 = sanitize_filename(data.get('file2'))

        path1 = os.path.join(app.config['UPLOAD_FOLDER'], file1)
        path2 = os.path.join(app.config['UPLOAD_FOLDER'], file2)

        if not os.path.exists(path1) or not os.path.exists(path2):
            return {'error': '파일이 존재하지 않습니다.'}, 404

        # 기준 엑셀: 1행, 열 방향
        df_base = pd.read_excel(path1, index_col=0, header=None).T

        # 병합 엑셀: 인덱스가 이름들, 열이 값
        df_merge = pd.read_excel(path2, index_col=0)

        # 기준에 없는 인덱스만 추출 → 공통 컬럼만 필터링
        new_rows = df_merge[~df_merge.index.isin(df_base.index)]
        common_columns = df_base.columns.intersection(df_merge.columns)
        new_rows_filtered = new_rows[common_columns]

        # 병합 결과
        df_result = pd.concat([df_base, new_rows_filtered])

        # 메모리로 엑셀 저장
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_result.to_excel(writer, sheet_name='Merged', index=True)
        output.seek(0)

        return send_file(output,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name='merged_result.xlsx')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Render 배포용 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
