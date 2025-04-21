# Import eventlet first and monkey patch
import eventlet
eventlet.monkey_patch()

# Standard library imports
import cv2
import base64
import json
import threading
from datetime import datetime

# Flask and SocketIO imports
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit

# Local imports
from detector.yolo import YOLODetector
from counter.counter import PersonCounter
from utils.visualization import draw_results

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Add a secret key
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')

# Global variables
with app.app_context():
    detector = YOLODetector()
    counter = PersonCounter()
    sensitivity = "Medium"
    current_camera = 0
    stats = {
        "current_count": 0,
        "average": 0,
        "minimum": 0,
        "peak": 0,
        "total_counts": []
    }
    logs = []

class VideoCamera:
    def __init__(self):
        self.video = cv2.VideoCapture(current_camera)
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video.set(cv2.CAP_PROP_FPS, 30)
        self.lock = eventlet.semaphore.Semaphore()  # Use eventlet's semaphore
        self.is_tracking = False

    def __del__(self):
        self.video.release()

    def get_frame(self):
        with self.lock:
            success, frame = self.video.read()
            if not success:
                return None

            if self.is_tracking:
                with app.app_context():
                    detections = detector.detect(frame)
                    count = counter.update(detections)
                    frame = draw_results(frame, detections, count)
                    
                    # Update statistics
                    stats["current_count"] = count
                    stats["total_counts"].append(count)
                    stats["average"] = sum(stats["total_counts"]) / len(stats["total_counts"])
                    stats["minimum"] = min(stats["total_counts"])
                    stats["peak"] = max(stats["total_counts"])
                    
                    socketio.emit('stats_update', stats)

            # Encode the frame
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return jpeg.tobytes()

video_stream = VideoCamera()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

def generate_frames():
    while True:
        frame = video_stream.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        eventlet.sleep(0.033)  # ~30 FPS

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('toggle_tracking')
def handle_tracking(data):
    global video_stream
    video_stream.is_tracking = data['tracking']
    log_message(f"Tracking {'started' if video_stream.is_tracking else 'stopped'}")

@socketio.on('change_camera')
def handle_camera(data):
    global video_stream, current_camera
    current_camera = int(data['camera'])
    if video_stream:
        del video_stream
    video_stream = VideoCamera()
    log_message(f"Changed to camera {current_camera}")

@socketio.on('change_sensitivity')
def handle_sensitivity(data):
    global sensitivity
    sensitivity = data['level']
    log_message(f"Detection sensitivity set to {sensitivity}")

def log_message(message):
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message
    })
    socketio.emit('log_update', logs[-1])

# Ensure camera is released when the application stops
def cleanup():
    if video_stream:
        del video_stream

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    # Use eventlet's WSGI server instead of Flask's default
    socketio.run(app, 
                debug=True, 
                host='0.0.0.0', 
                port=5000,
                use_reloader=False)  # Disable reloader to prevent camera issues