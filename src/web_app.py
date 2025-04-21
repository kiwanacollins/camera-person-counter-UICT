# Import eventlet first and monkey patch
import eventlet
eventlet.monkey_patch()

# Standard library imports
import cv2
import base64
import json
import threading
import os
import csv
import time
import io
from datetime import datetime, timedelta

# Flask and SocketIO imports
from flask import Flask, render_template, Response, jsonify, send_file, request
from flask_socketio import SocketIO, emit

# Local imports
from detector.yolo import YOLODetector
from counter.counter import PersonCounter
from utils.visualization import draw_results
from camera.picamera_fixed import Camera  # Using the fixed camera implementation

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Add a secret key
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')

# Global variables
with app.app_context():
    detector = YOLODetector()
    counter = PersonCounter()
    sensitivity = "Medium"
    current_camera = 0  # Using /dev/video0 which is the video capture interface
    is_paused = False
    last_frame = None
    system_status = "Active"
    logging_enabled = True
    logging_frequency = 60  # seconds
    last_log_time = datetime.now()
    stats = {
        "current_count": 0,
        "average": 0,
        "minimum": 0,
        "peak": 0,
        "total_counts": []
    }
    logs = []
    errors = []

class VideoCamera:
    def __init__(self):
        global current_camera
        print(f"Initializing camera with ID 0")  # Changed to always try video0 first
        current_camera = 0  # Changed from 1 to 0
        retries = 3
        last_error = None
        
        for attempt in range(retries):
            try:
                self.camera = Camera(camera_id=current_camera)
                self.camera.start_camera()
                print("Camera initialized successfully")
                break
            except Exception as e:
                last_error = str(e)
                print(f"Attempt {attempt + 1}/{retries} failed: {str(e)}")
                if attempt < retries - 1:
                    print("Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                raise RuntimeError(f"Failed to initialize camera after {retries} attempts. Last error: {last_error}")
        
        self.lock = eventlet.semaphore.Semaphore()
        self.is_tracking = False
        self.last_frame = None
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.fps = 0

    def __del__(self):
        self.camera.stop_camera()

    def get_frame(self):
        global is_paused, last_frame, system_status, last_log_time, logs, logging_enabled, logging_frequency
        
        if is_paused and self.last_frame is not None:
            return self.last_frame
            
        with self.lock:
            success, frame = self.camera.capture_frame()
            
            # Calculate FPS
            self.frame_count += 1
            elapsed_time = time.time() - self.fps_start_time
            if elapsed_time > 1.0:
                self.fps = self.frame_count / elapsed_time
                self.frame_count = 0
                self.fps_start_time = time.time()
            
            if not success:
                system_status = "Error"
                add_error("camera-disconnected", "Camera disconnected", 
                         "The camera connection has been lost. Please check your camera settings.")
                socketio.emit('system_status', {'state': system_status, 'message': 'Camera disconnected'})
                return None
            else:
                system_status = "Active"

            if self.is_tracking:
                with app.app_context():
                    try:
                        # Set sensitivity based on the global setting
                        sensitivity_values = {
                            "Low": 0.4,
                            "Medium": 0.5,
                            "High": 0.6
                        }
                        detector.confidence_threshold = sensitivity_values.get(sensitivity, 0.5)
                        
                        detections = detector.detect(frame)
                        count = counter.update(detections)
                        frame = draw_results(frame, detections, count)
                        
                        # Update statistics
                        stats["current_count"] = count
                        stats["total_counts"].append(count)
                        stats["average"] = sum(stats["total_counts"]) / len(stats["total_counts"])
                        stats["minimum"] = min(stats["total_counts"])
                        stats["peak"] = max(stats["total_counts"])
                        
                        # Limit stats history to prevent memory issues
                        if len(stats["total_counts"]) > 1000:
                            stats["total_counts"] = stats["total_counts"][-1000:]
                            
                        socketio.emit('stats_update', stats)
                        
                        # Log data based on frequency setting
                        if logging_enabled:
                            current_time = datetime.now()
                            if (current_time - last_log_time).total_seconds() >= logging_frequency:
                                log_entry = {
                                    "timestamp": current_time.isoformat(),
                                    "count": count,
                                    "status": system_status
                                }
                                logs.append(log_entry)
                                
                                # Limit logs to 10000 entries
                                if len(logs) > 10000:
                                    logs = logs[-10000:]
                                    
                                last_log_time = current_time
                    except Exception as e:
                        print(f"Error during detection: {str(e)}")
                        system_status = "Error"
                        add_error("detection-error", "Detection error", 
                                 f"An error occurred during people detection: {str(e)}")
                        socketio.emit('system_status', {'state': system_status, 'message': 'Detection error'})

            # Check for low frame rate
            if self.fps < 10 and self.is_tracking:
                system_status = "Warning"
                add_error("low-fps", "Low frame rate detected", 
                         f"The current frame rate ({self.fps:.1f} FPS) is lower than recommended. This may affect detection accuracy.")
                socketio.emit('system_status', {'state': system_status, 'message': 'Low frame rate'})
                
            # Add FPS to frame
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Encode the frame
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            self.last_frame = jpeg.tobytes()
            last_frame = self.last_frame
            return self.last_frame

video_stream = VideoCamera()

@app.route('/')
def index():
    return render_template('index.html')

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

def log_message(message):
    """Add a message to the logs with timestamp"""
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "count": stats["current_count"],
        "status": system_status
    })

def add_error(error_id, message, details):
    """Add an error to the error list if it doesn't already exist"""
    # Check if error with this ID already exists
    for error in errors:
        if error["id"] == error_id:
            return
    
    errors.append({
        "id": error_id,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    socketio.emit('new_error', {
        "id": error_id,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })

@socketio.on('toggle_tracking')
def handle_tracking(data):
    global video_stream
    video_stream.is_tracking = data['tracking']
    log_message(f"Tracking {'started' if video_stream.is_tracking else 'stopped'}")

@socketio.on('pause_video')
def handle_pause(data):
    global is_paused
    is_paused = data['paused']
    log_message(f"Video feed {'paused' if is_paused else 'resumed'}")

@socketio.on('change_camera')
def handle_camera_change(data):
    global current_camera, video_stream
    try:
        new_camera = int(data['camera'])
        if new_camera != current_camera:
            current_camera = new_camera
            # Recreate the video stream with the new camera
            video_stream = VideoCamera()
            log_message(f"Camera changed to {current_camera}")
    except Exception as e:
        add_error("camera-change-error", "Camera change failed", str(e))

@socketio.on('save_config')
def handle_save_config(data):
    global sensitivity, logging_enabled, logging_frequency
    
    try:
        # Update sensitivity
        if 'sensitivity' in data:
            sensitivity = data['sensitivity']
        
        # Update logging settings
        if 'logging' in data:
            logging_enabled = data['logging'].get('enabled', True)
            logging_frequency = int(data['logging'].get('frequency', 60))
        
        log_message(f"Configuration updated: Sensitivity={sensitivity}, Logging={logging_enabled}, Frequency={logging_frequency}s")
    except Exception as e:
        add_error("config-save-error", "Failed to save configuration", str(e))

@socketio.on('test_camera')
def handle_test_camera(data):
    camera_id = int(data['camera'])
    try:
        test_cam = cv2.VideoCapture(camera_id)
        if test_cam.isOpened():
            test_cam.release()
            socketio.emit('camera_test_result', {
                'success': True,
                'message': f"Camera {camera_id} is working properly"
            })
        else:
            socketio.emit('camera_test_result', {
                'success': False,
                'message': f"Camera {camera_id} cannot be opened"
            })
            add_error(f"camera-test-{camera_id}", f"Camera {camera_id} test failed", 
                     f"Could not access camera {camera_id}. Please check if it's connected properly.")
    except Exception as e:
        socketio.emit('camera_test_result', {
            'success': False,
            'message': str(e)
        })
        add_error(f"camera-test-{camera_id}", f"Camera {camera_id} test error", str(e))

@socketio.on('refresh_stats')
def handle_refresh_stats():
    socketio.emit('stats_update', stats)
    log_message("Statistics manually refreshed")

@app.route('/export_logs_csv')
def export_logs_csv():
    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Count', 'Status'])
    
    # Filter logs by date range if provided
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filtered_logs = logs
    
    if start_date:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        filtered_logs = [log for log in filtered_logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) >= start]
        
    if end_date:
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        filtered_logs = [log for log in filtered_logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) <= end]
    
    for log in filtered_logs:
        writer.writerow([
            log.get('timestamp', ''),
            log.get('count', 0),
            log.get('status', '')
        ])
    
    # Create Flask response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'person_counter_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/get_all_logs')
def get_all_logs():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filtered_logs = logs
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            filtered_logs = [log for log in filtered_logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) >= start]
        except ValueError:
            pass
        
    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            filtered_logs = [log for log in filtered_logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) <= end]
        except ValueError:
            pass
    
    return jsonify(filtered_logs)

@app.route('/get_all_errors')
def get_all_errors():
    return jsonify(errors)

@socketio.on('clear_errors')
def handle_clear_errors():
    global errors
    errors = []
    log_message("All errors cleared")

@socketio.on('resolve_error')
def handle_resolve_error(data):
    global errors
    error_id = data.get('id')
    if error_id:
        errors = [error for error in errors if error['id'] != error_id]
        log_message(f"Error {error_id} resolved")

if __name__ == '__main__':
    # Try to initialize the video stream with retries
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            video_stream = VideoCamera()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Failed to initialize camera (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to initialize camera after {max_retries} attempts. Last error: {str(e)}")
                raise
    
    socketio.run(app, debug=False, host='0.0.0.0')