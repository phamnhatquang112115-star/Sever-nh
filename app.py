from flask import Flask, request, jsonify
import os
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import io
import asyncio
import websockets
import base64

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 🔐 Token XiaoZhi MCP
XIAOZHI_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjYwNDk4NCwiYWdlbnRJZCI6OTg4NDIyLCJlbmRwb2ludElkIjoiYWdlbnRfOTg4NDIyIiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc2MjQzMDUxMSwiZXhwIjoxNzkzOTg4MTExfQ.bGhpsiRJM6l_zGhgymwUOZ8CErz7JZcCFGPkrVkGZ0PCnzaSn5yr6qJOtwHZoqApkf9cEKfq5eEtjPuMmim3_w"

async def send_to_xiaozhi(image_bytes):
    try:
        async with websockets.connect(XIAOZHI_URL) as ws:
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')
            await ws.send(img_b64)
            response = await ws.recv()
            return response
    except Exception as e:
        return f"Lỗi gửi XiaoZhi: {e}"

def extract_text(image_path):
    return "OCR đã tắt"

def match_template_orb(image_path, template_path):
    try:
        img1 = cv2.imread(template_path, 0)
        img2 = cv2.imread(image_path, 0)
        orb = cv2.ORB_create()
        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)
        if des1 is None or des2 is None:
            return False
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        good_matches = [m for m in matches if m.distance < 50]
        return len(good_matches) >= 10
    except:
        return False

def match_all_templates(image_path):
    matched = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename.startswith("compare_") or not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        template_path = os.path.join(UPLOAD_FOLDER, filename)
        if match_template_orb(image_path, template_path):
            matched.append(filename)
    return matched

@app.route('/upload_sample', methods=['POST'])
def upload_sample():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'status': 'error', 'message': 'Thiếu tên ảnh mẫu'})
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(request.data)
    return jsonify({'status': 'ok', 'message': f'Đã lưu ảnh mẫu: {filename}'})

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
    matched_templates = match_all_templates(filepath)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    xiaozhi_result = loop.run_until_complete(send_to_xiaozhi(image_data))

    return jsonify({
        'status': 'ok',
        'filename': filename,
        'resolution': resolution,
        'text_found': text,
        'matched_templates': matched_templates,
        'xiaozhi_result': xiaozhi_result
    })

@app.route('/')
def index():
    return '''
    <h2>ESP32-CAM Server is running!</h2>
    <ul>
        <li><a href="/upload_sample_form">Gửi ảnh mẫu</a></li>
        <li><a href="/upload_form">Gửi ảnh kiểm tra</a></li>
        <li><a href="/list_uploads_html">Xem ảnh đã upload</a></li>
    </ul>
    '''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)