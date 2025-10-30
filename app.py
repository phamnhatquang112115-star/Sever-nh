from flask import Flask, request, render_template_string
import cv2
import numpy as np
import pytesseract
import os

app = Flask(__name__)

# Nếu chạy trên Render, không cần chỉ định đường dẫn Tesseract
# Nếu chạy cục bộ trên Windows, bạn có thể bật dòng dưới:
# pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

# Tạo thư mục lưu mẫu nếu chưa có
os.makedirs('samples', exist_ok=True)

# Giao diện HTML
HTML = '''
<h2>📸 Nhận dạng ký hiệu trên remote</h2>

<h3>1. Tải ảnh mẫu</h3>
<form method="POST" action="/upload_sample" enctype="multipart/form-data">
    <input type="file" name="image">
    <input type="submit" value="Upload Sample">
</form>

<h3>2. Tải ảnh mới để so sánh</h3>
<form method="POST" action="/upload" enctype="multipart/form-data">
    <input type="file" name="image">
    <input type="submit" value="Upload & Compare">
</form>

{% if result %}
<h3>Kết quả so sánh:</h3>
<pre>{{ result }}</pre>
{% endif %}
'''

# Route trang chủ
@app.route('/')
def index():
    return render_template_string(HTML)

# Route upload ảnh mẫu
@app.route('/upload_sample', methods=['POST'])
def upload_sample():
    file = request.files['image']
    img_bytes = file.read()
    with open('samples/sample.jpg', 'wb') as f:
        f.write(img_bytes)
    return render_template_string(HTML, result="✅ Ảnh mẫu đã được lưu.")

# Route upload ảnh mới và so sánh
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    img_bytes = file.read()
    npimg = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # Xử lý ảnh mới
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
    text_new = pytesseract.image_to_string(thresh)

    # Đọc ảnh mẫu
    if not os.path.exists('samples/sample.jpg'):
        return render_template_string(HTML, result="❌ Chưa có ảnh mẫu để so sánh.")

    sample_img = cv2.imread('samples/sample.jpg')
    gray_sample = cv2.cvtColor(sample_img, cv2.COLOR_BGR2GRAY)
    thresh_sample = cv2.threshold(gray_sample, 150, 255, cv2.THRESH_BINARY)[1]
    text_sample = pytesseract.image_to_string(thresh_sample)

    # So sánh kết quả OCR
    result = f"📌 Ảnh mẫu:\n{text_sample}\n\n📷 Ảnh mới:\n{text_new}"

    return render_template_string(HTML, result=result)

# Khởi động Flask với cổng do Render cung cấp
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)