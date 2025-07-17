import os
import re
from flask import Flask, render_template, request, jsonify, send_file
from urllib.parse import quote
import pandas as pd
import fitz  # PyMuPDF
import docx  # python-docx
import io    # for Excel file buffer

app = Flask(__name__)

# 업로드 폴더 설정
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 한글+보안 허용 파일명 필터링
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

# 키워드로 파일 검색
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

# ✅ 병합된 엑셀 다운로드 API
@app.route('/merge_custom_horizontal_named', methods=['POST'])
def merge_custom_horizontal_named():
    try:
        data = request.get_json()
        file1 = sanitize_filename(data.get('file1'))  # 기준 엑셀
        file2 = sanitize_filename(data.get('file2'))  # 병합 엑셀

        path1 = os.path.join(app.config['UPLOAD_FOLDER'], file1)
        path2 = os.path.join(app.config['UPLOAD_FOLDER'], file2)

        if not os.path.exists(path1) or not os.path.exists(path2):
            return jsonify({'error': '파일이 존재하지 않습니다.'}), 404

        # 기준 엑셀: 1행, 가로 방향
        df_base = pd.read_excel(path1, index_col=0, header=None).T

        # 병합 엑셀: 행 방향, 인덱스가 이름
        df_merge = pd.read_excel(path2, index_col=0)

        # 기준에 없는 인덱스만 추출
        new_rows = df_merge[~df_merge.index.isin(df_base.index)]

        # 기준 엑셀의 컬럼만 유지 (없는 건 NaN)
        new_rows_filtered = new_rows.reindex(columns=df_base.columns)

        # 병합
        df_result = pd.concat([df_base, new_rows_filtered])
        df_result.fillna("", inplace=True)  # NaN → 빈 칸 처리

        # 메모리에 엑셀 저장
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

# 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
