from flask import Flask, request, jsonify, send_from_directory
import os
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Hàm trích xuất văn bản từ ảnh (OCR đã tắt)
def extract_text(image_path):
    return "OCR đã tắt"

# Hàm so khớp biểu tượng mẫu
def match_template(image_path, template_path):
    try:
        img = cv2.imread(image_path, 0)
        template = cv2.imread(template_path, 0)
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        return len(loc[0]) > 0
    except Exception as e:
        print(f"Lỗi khớp biểu tượng: {e}")
        return False

# API nhận ảnh mẫu từ ESP32-CAM
@app.route('/upload_sample', methods=['POST'])
def upload_sample():
    image_data = request.data
    filename = 'cool_icon.jpg'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(image_data)
    return jsonify({'status': 'ok', 'message': 'Ảnh mẫu đã lưu', 'filename': filename})

# API nhận ảnh cần xử lý từ ESP32-CAM
@app.route('/upload_compare', methods=['POST'])
def upload_compare():
    image_data = request.data
    filename = f'compare_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(image_data)

    try:
        img = Image.open(io.BytesIO(image_data))
        resolution = f'{img.width}x{img.height}'
    except:
        resolution = 'unknown'

    text = extract_text(filepath)
    has_cool = False  # OCR đã tắt nên không kiểm tra chữ "cool"

    template_path = os.path.join(UPLOAD_FOLDER, 'cool_icon.jpg')
    matched_icon = match_template(filepath, template_path) if os.path.exists(template_path) else None

    return jsonify({
        'status': 'ok',
        'filename': filename,
        'resolution': resolution,
        'text_found': text,
        'has_cool_text': has_cool,
        'matched_icon': matched_icon
    })

# Giao diện web để tải ảnh lên
@app.route('/upload_form')
def upload_form():
    return '''
    <h2>Tải ảnh lên để xử lý</h2>
    <form action="/upload_compare_form" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*">
        <button type="submit">Gửi ảnh</button>
    </form>
    '''

# Xử lý ảnh từ form web
@app.route('/upload_compare_form', methods=['POST'])
def upload_compare_form():
    file = request.files.get('file')
    if not file:
        return 'Không có ảnh được gửi lên.'

    filename = f'compare_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        img = Image.open(filepath)
        resolution = f'{img.width}x{img.height}'
    except:
        resolution = 'unknown'

    text = extract_text(filepath)
    has_cool = False  # OCR đã tắt nên không kiểm tra chữ "cool"

    template_path = os.path.join(UPLOAD_FOLDER, 'cool_icon.jpg')
    matched_icon = match_template(filepath, template_path) if os.path.exists(template_path) else None

    return f'''
    <h3>Kết quả xử lý ảnh:</h3>
    <ul>
        <li>Tên file: {filename}</li>
        <li>Độ phân giải: {resolution}</li>
        <li>Văn bản tìm thấy: {text}</li>
        <li>Có chữ "cool": {has_cool}</li>
        <li>Khớp biểu tượng mẫu: {matched_icon}</li>
    </ul>
    <a href="/upload_form">Tải ảnh khác</a>
    '''

# API kiểm tra ảnh đã upload
@app.route('/list_uploads', methods=['GET'])
def list_uploads():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        images = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        return jsonify({'status': 'ok', 'images': images})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Trang chủ đơn giản
@app.route('/')
def index():
    return 'ESP32-CAM Server is running!'

# Khởi chạy server (tương thích Render)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)