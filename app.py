from flask import Flask, request, jsonify
import os
from datetime import datetime
import cv2
import pytesseract
import numpy as np
from PIL import Image
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_text(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return text.strip()

def match_template(image_path, template_path):
    try:
        img = cv2.imread(image_path, 0)
        template = cv2.imread(template_path, 0)
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        return len(loc[0]) > 0
    except:
        return False

@app.route('/upload_sample', methods=['POST'])
def upload_sample():
    image_data = request.data
    filename = f'sample_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(image_data)
    return jsonify({'status': 'ok', 'message': 'Sample saved', 'filename': filename})

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
    has_cool = "cool" in text.lower()

    # Nếu bạn có ảnh mẫu, đặt tên là 'cool_icon.jpg' trong thư mục uploads
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

@app.route('/')
def index():
    return 'ESP32-CAM Server is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)