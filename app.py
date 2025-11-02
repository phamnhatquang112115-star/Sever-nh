from flask import Flask, request, jsonify
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

# Hàm so khớp biểu tượng mẫu bằng ORB
def match_template_orb(image_path, template_path):
    try:
        img1 = cv2.imread(template_path, 0)
        img2 = cv2.imread(image_path, 0)

        orb = cv2.ORB_create()
        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)

        if des1 is None or des2 is None:
            print(f"Không tìm thấy đặc trưng trong {template_path}")
            return False

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)

        good_matches = [m for m in matches if m.distance < 50]
        print(f"Số điểm khớp tốt với {template_path}: {len(good_matches)}")
        return len(good_matches) >= 10
    except Exception as e:
        print(f"Lỗi ORB matching với {template_path}: {e}")
        return False

# Hàm so khớp với tất cả ảnh mẫu đã lưu
def match_all_templates(image_path):
    matched = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename.startswith("compare_") or not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        template_path = os.path.join(UPLOAD_FOLDER, filename)
        if match_template_orb(image_path, template_path):
            matched.append(filename)
    return matched

# API nhận ảnh mẫu từ ESP32-CAM
@app.route('/upload_sample', methods=['POST'])
def upload_sample():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'status': 'error', 'message': 'Thiếu tên ảnh mẫu (filename)'})
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(request.data)
    
    return jsonify({'status': 'ok', 'message': f'Đã lưu ảnh mẫu: {filename}'})

# Giao diện web để gửi ảnh mẫu
@app.route('/upload_sample_form')
def upload_sample_form():
    return '''
    <h2>Gửi ảnh mẫu lên server</h2>
    <form action="/upload_sample_form_post" method="post" enctype="multipart/form-data">
        <input type="text" name="filename" placeholder="Tên ảnh mẫu (ví dụ: mode_Cool.jpg)" required><br><br>
        <input type="file" name="file" accept="image/*" required><br><br>
        <button type="submit">Gửi ảnh mẫu</button>
    </form>
    '''

@app.route('/upload_sample_form_post', methods=['POST'])
def upload_sample_form_post():
    file = request.files.get('file')
    filename = request.form.get('filename')
    if not file or not filename:
        return 'Thiếu ảnh hoặc tên ảnh mẫu.'

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    return f'''
    <h3>Đã lưu ảnh mẫu thành công!</h3>
    <ul>
        <li>Tên ảnh: {filename}</li>
        <li>Đường dẫn: {filepath}</li>
    </ul>
    <a href="/upload_sample_form">Gửi ảnh khác</a>
    '''

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
    has_cool = False

    matched_templates = match_all_templates(filepath)

    return jsonify({
        'status': 'ok',
        'filename': filename,
        'resolution': resolution,
        'text_found': text,
        'has_cool_text': has_cool,
        'matched_templates': matched_templates
    })

# Giao diện web để tải ảnh kiểm tra
@app.route('/upload_form')
def upload_form():
    return '''
    <h2>Tải ảnh lên để xử lý</h2>
    <form action="/upload_compare_form" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*">
        <button type="submit">Gửi ảnh</button>
    </form>
    '''

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
    has_cool = False

    matched_templates = match_all_templates(filepath)
    matched_html = "<br>".join(matched_templates) if matched_templates else "Không khớp biểu tượng nào"

    return f'''
    <h3>Kết quả xử lý ảnh:</h3>
    <ul>
        <li>Tên file: {filename}</li>
        <li>Độ phân giải: {resolution}</li>
        <li>Văn bản tìm thấy: {text}</li>
        <li>Có chữ "cool": {has_cool}</li>
        <li>Biểu tượng khớp: <br>{matched_html}</li>
    </ul>
    <a href="/upload_form">Tải ảnh khác</a>
    '''

# Giao diện web xem danh sách ảnh đã upload
@app.route('/list_uploads_html')
def list_uploads_html():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        images = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        html = "<h2>Danh sách ảnh đã upload:</h2><ul>"
        for img in images:
            html += f'<li>{img}</li>'
        html += "</ul><a href='/'>Trang chủ</a>"
        return html
    except Exception as e:
        return f"Lỗi: {str(e)}"

# API JSON kiểm tra ảnh đã upload
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
    return '''
    <h2>ESP32-CAM Server is running!</h2>
    <ul>
        <li><a href="/upload_form">Gửi ảnh kiểm tra</a></li>
        <li><a href="/upload_sample_form">Gửi ảnh mẫu</a></li>
        <li><a href="/list_uploads_html">Xem ảnh đã upload</a></li>
    </ul>
    '''

# Khởi chạy server
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)