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
    
@app.route('/config')
def config():
    return render_template('config.html')
    
@app.route('/logs')
def logs_page():
    return render_template('logs.html')
    
@app.route('/errors')
def errors():
    return render_template('errors.html')

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

# System Configuration handlers
@socketio.on('update_config')
def handle_config_update(config):
    global sensitivity, current_camera
    try:
        # Update camera settings
        camera_id = int(config['camera']['id'])
        if camera_id != current_camera:
            current_camera = camera_id
            global video_stream
            if video_stream:
                del video_stream
            video_stream = VideoCamera()
            
        # Update detection settings
        if 'detection' in config:
            sensitivity_map = {
                "1": "Low", 
                "2": "Medium", 
                "3": "High"
            }
            if 'sensitivity' in config['detection'] and str(config['detection']['sensitivity']) in sensitivity_map:
                sensitivity = sensitivity_map[str(config['detection']['sensitivity'])]
        
        # Log the configuration update
        log_message(f"System configuration updated")
        return {'success': True, 'message': 'Configuration updated successfully'}
    except Exception as e:
        log_message(f"Error updating configuration: {str(e)}")
        return {'success': False, 'message': f'Error: {str(e)}'}

@socketio.on('test_camera')
def handle_test_camera(data):
    try:
        camera_id = int(data['camera'])
        # In a real implementation, you might want to create a temporary camera 
        # to test without disrupting the main video stream
        log_message(f"Testing camera {camera_id}")
        return {'success': True}
    except Exception as e:
        log_message(f"Error testing camera: {str(e)}")
        return {'success': False, 'message': f'Error: {str(e)}'}

# Logs and Reports handlers
@socketio.on('get_logs')
def handle_get_logs(data):
    try:
        # In a real implementation, you might want to filter logs based on data parameters
        # For now, we'll just return all logs
        log_data = []
        for i, log in enumerate(logs):
            # Convert log entry to the format expected by the client
            status = 'normal'
            count = stats["current_count"] if i == len(logs) - 1 else 0
            if "error" in log["message"].lower():
                status = 'error'
            elif "warn" in log["message"].lower():
                status = 'warning'
            
            log_data.append({
                'id': i + 1,
                'timestamp': log["timestamp"],
                'count': count,
                'status': status,
                'message': log["message"]
            })
        
        return {'success': True, 'logs': log_data}
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}

# Error Notification handlers
@socketio.on('get_errors')
def handle_get_errors(data):
    try:
        # Filter logs to find error entries
        error_logs = []
        for i, log in enumerate(logs):
            if "error" in log["message"].lower():
                severity = 'high'
            elif "warn" in log["message"].lower():
                severity = 'medium'
            else:
                continue  # Skip non-error/warning logs
                
            error_logs.append({
                'id': i + 1,
                'title': log["message"].split(":")[0] if ":" in log["message"] else "System Error",
                'message': log["message"],
                'timestamp': log["timestamp"],
                'severity': severity,
                'status': 'active'
            })
        
        return {'success': True, 'errors': error_logs}
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}

@socketio.on('fix_error')
def handle_fix_error(data):
    try:
        error_id = data['errorId']
        # In a real implementation, you would attempt to fix the error based on its type
        log_message(f"Attempted to fix error #{error_id}")
        return {'success': True, 'message': f'Error #{error_id} fix attempt completed'}
    except Exception as e:
        log_message(f"Error during fix attempt: {str(e)}")
        return {'success': False, 'message': f'Error: {str(e)}'}

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