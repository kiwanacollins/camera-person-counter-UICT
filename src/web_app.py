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
    frame_width = 640
    frame_height = 480
    frame_rate = 30
    confidence_threshold = 0.5
    logging_enabled = True
    log_frequency = 60  # in seconds
    log_events = True
    log_errors = True
    last_log_time = datetime.now()
    system_status = "normal"  # normal, warning, or error
    stats = {
        "current_count": 0,
        "average": 0,
        "minimum": 0,
        "peak": 0,
        "total_counts": [],
        "frame_rate": 0,
        "detection_time": 0,
        "system_load": 0
    }
    logs = []
    errors = []

class VideoCamera:
    def __init__(self):
        self.video = cv2.VideoCapture(current_camera)
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        self.video.set(cv2.CAP_PROP_FPS, frame_rate)
        self.lock = eventlet.semaphore.Semaphore()  # Use eventlet's semaphore
        self.is_tracking = False
        self.frame_count = 0
        self.fps_start_time = datetime.now()
        self.actual_fps = 0
        self.last_error_check = datetime.now()

    def __del__(self):
        self.video.release()

    def get_frame(self):
        global system_status, last_log_time
        
        with self.lock:
            # Check camera status
            success, frame = self.video.read()
            if not success:
                log_message("Error: Failed to read frame from camera", "error")
                system_status = "error"
                return None

            start_time = datetime.now()
            self.frame_count += 1
            current_time = datetime.now()
            
            # Calculate actual FPS every second
            time_diff = (current_time - self.fps_start_time).total_seconds()
            if time_diff >= 1.0:
                self.actual_fps = self.frame_count / time_diff
                stats["frame_rate"] = round(self.actual_fps, 1)
                self.frame_count = 0
                self.fps_start_time = current_time
                
                # Check if frame rate is too low (possible performance issue)
                if self.actual_fps < (frame_rate * 0.7) and self.actual_fps > 0:
                    log_message(f"Warning: Low frame rate detected ({self.actual_fps:.1f} FPS)", "warning")
                    system_status = "warning"

            if self.is_tracking:
                try:
                    with app.app_context():
                        # Measure detection time for performance monitoring
                        detect_start = datetime.now()
                        detections = detector.detect(frame, confidence_threshold)
                        count = counter.update(detections)
                        frame = draw_results(frame, detections, count)
                        detect_time = (datetime.now() - detect_start).total_seconds() * 1000  # in milliseconds
                        stats["detection_time"] = round(detect_time, 1)
                        
                        # Update statistics
                        stats["current_count"] = count
                        stats["total_counts"].append(count)
                        stats["average"] = sum(stats["total_counts"]) / len(stats["total_counts"])
                        stats["minimum"] = min(stats["total_counts"])
                        stats["peak"] = max(stats["total_counts"])
                        
                        # Add system load (CPU usage would go here in a real implementation)
                        stats["system_load"] = min(90, stats["detection_time"] / 10)  # Simplified for demo
                        
                        # Log based on frequency settings if enabled
                        if logging_enabled and (current_time - last_log_time).total_seconds() >= log_frequency:
                            log_message(f"Current count: {count} people detected", "info")
                            last_log_time = current_time
                        
                        socketio.emit('stats_update', stats)
                except Exception as e:
                    log_message(f"Error during detection: {str(e)}", "error")
                    system_status = "error"

            # Check for potential errors every 5 seconds
            if (current_time - self.last_error_check).total_seconds() >= 5:
                self.last_error_check = current_time
                
                # Check if camera resolution is as expected
                actual_width = self.video.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.video.get(cv2.CAP_PROP_FRAME_HEIGHT)
                if actual_width != frame_width or actual_height != frame_height:
                    log_message(f"Warning: Camera resolution mismatch. Expected: {frame_width}x{frame_height}, Got: {actual_width}x{actual_height}", "warning")
                    system_status = "warning"
                
                # Example of auto-recovery (this could be expanded in a real system)
                if stats["system_load"] > 80:
                    log_message("Warning: High system load detected", "warning")
                    system_status = "warning"

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
    global sensitivity, current_camera, frame_width, frame_height, frame_rate
    global confidence_threshold, logging_enabled, log_frequency, log_events, log_errors
    
    try:
        # Update camera settings
        if 'camera' in config:
            camera_id = int(config['camera']['id'])
            camera_changed = False
            
            # Check if we need to update camera
            if camera_id != current_camera:
                current_camera = camera_id
                camera_changed = True
                
            # Update resolution if provided
            if 'resolution' in config['camera']:
                resolution = config['camera']['resolution'].split('x')
                new_width = int(resolution[0])
                new_height = int(resolution[1])
                if new_width != frame_width or new_height != frame_height:
                    frame_width = new_width
                    frame_height = new_height
                    camera_changed = True
                    
            # Update frame rate if provided
            if 'frameRate' in config['camera']:
                new_frame_rate = int(config['camera']['frameRate'])
                if new_frame_rate != frame_rate:
                    frame_rate = new_frame_rate
                    camera_changed = True
                    
            # Recreate the video stream if camera settings changed
            if camera_changed:
                global video_stream
                if video_stream:
                    del video_stream
                video_stream = VideoCamera()
                log_message(f"Camera configuration updated: Camera {current_camera}, {frame_width}x{frame_height} @ {frame_rate}fps", "info")
            
        # Update detection settings
        if 'detection' in config:
            sensitivity_map = {
                "1": "Low", 
                "2": "Medium", 
                "3": "High"
            }
            
            if 'sensitivity' in config['detection'] and str(config['detection']['sensitivity']) in sensitivity_map:
                new_sensitivity = sensitivity_map[str(config['detection']['sensitivity'])]
                if new_sensitivity != sensitivity:
                    sensitivity = new_sensitivity
                    log_message(f"Detection sensitivity set to {sensitivity}", "info")
            
            if 'confidenceThreshold' in config['detection']:
                new_threshold = float(config['detection']['confidenceThreshold']) / 100.0  # Convert from percentage
                if new_threshold != confidence_threshold:
                    confidence_threshold = new_threshold
                    log_message(f"Detection confidence threshold set to {confidence_threshold:.2f}", "info")
        
        # Update logging preferences
        if 'logging' in config:
            if 'enabled' in config['logging']:
                logging_enabled = bool(config['logging']['enabled'])
                
            if 'frequency' in config['logging']:
                log_frequency = int(config['logging']['frequency'])
                
            if 'logEvents' in config['logging']:
                log_events = bool(config['logging']['logEvents'])
                
            if 'logErrors' in config['logging']:
                log_errors = bool(config['logging']['logErrors'])
                
            log_message(f"Logging preferences updated: enabled={logging_enabled}, frequency={log_frequency}s", "info")
        
        # Log the overall configuration update
        log_message(f"System configuration updated successfully", "info")
        return {'success': True, 'message': 'Configuration updated successfully'}
    except Exception as e:
        log_message(f"Error updating configuration: {str(e)}", "error")
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

def log_message(message, level="info"):
    """
    Enhanced logging function that tracks message level and updates error tracking.
    
    Args:
        message: The message to log
        level: The level of the message (info, warning, error)
    """
    global system_status
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "message": message,
        "level": level,
        "count": stats["current_count"]
    }
    
    # Only log if enabled or if it's an error (errors are always logged)
    if logging_enabled or level == "error":
        logs.append(log_entry)
        
        # Limit logs to prevent memory issues (keep last 1000 logs)
        if len(logs) > 1000:
            logs.pop(0)
            
        # Emit log update
        socketio.emit('log_update', log_entry)
    
    # Handle error tracking
    if level == "error" and log_errors:
        error_entry = {
            "id": len(errors) + 1,
            "timestamp": timestamp,
            "title": message.split(":")[0] if ":" in message else "System Error",
            "message": message,
            "severity": "high",
            "status": "active",
            "source": detect_error_source(message),
            "details": {
                "count": stats["current_count"],
                "frame_rate": stats["frame_rate"],
                "system_load": stats["system_load"]
            }
        }
        errors.append(error_entry)
        system_status = "error"
        socketio.emit('new_error', error_entry)
    elif level == "warning" and log_errors:
        error_entry = {
            "id": len(errors) + 1,
            "timestamp": timestamp,
            "title": message.split(":")[0] if ":" in message else "System Warning",
            "message": message,
            "severity": "medium",
            "status": "active",
            "source": detect_error_source(message),
            "details": {
                "count": stats["current_count"],
                "frame_rate": stats["frame_rate"],
                "system_load": stats["system_load"]
            }
        }
        errors.append(error_entry)
        if system_status != "error":  # Don't downgrade from error to warning
            system_status = "warning"
        socketio.emit('new_error', error_entry)

def detect_error_source(message):
    """
    Determine the source of an error based on the message content.
    """
    message = message.lower()
    if "camera" in message:
        return "camera"
    elif "detect" in message:
        return "detection"
    elif "frame" in message or "fps" in message:
        return "system"
    else:
        return "system"

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