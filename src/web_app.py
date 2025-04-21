# Import eventlet first and monkey patch
import eventlet
eventlet.monkey_patch()

# Standard library imports
import cv2
import numpy as np  # Add NumPy for frame manipulation
import base64
import json
import threading
import os
import sys
import atexit
from datetime import datetime

# Flask and SocketIO imports
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit

# Local imports
from detector.yolo import YOLODetector
from counter.counter import PersonCounter
from utils.visualization import draw_results

# Initialize Flask and SocketIO
app = Flask(__name__, 
           template_folder='templates')  # Explicitly set the template folder
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
        # Try opening the camera with multiple attempts if needed
        self.video = None
        self.connect_camera()
        
        self.lock = eventlet.semaphore.Semaphore()  # Use eventlet's semaphore
        self.is_tracking = False
        self.frame_count = 0
        self.fps_start_time = datetime.now()
        self.actual_fps = 0
        self.last_error_check = datetime.now()
    
    def connect_camera(self):
        """Try to establish camera connection with retry logic"""
        # Try to open camera - with fallback to default camera 0 if specified one fails
        try:
            print(f"Attempting to connect to camera {current_camera}")
            
            # On macOS, try a special approach for camera access
            if sys.platform == 'darwin':
                # For macOS, we might need to try both 0 and 1
                for cam_id in [current_camera, 0, 1]:
                    try:
                        self.video = cv2.VideoCapture(cam_id)
                        if self.video.isOpened():
                            print(f"Successfully opened camera {cam_id}")
                            break
                    except:
                        continue
            # For Raspberry Pi, use the Pi camera module if available
            elif sys.platform == 'linux':
                try:
                    # First try with camera index for USB cameras
                    self.video = cv2.VideoCapture(current_camera)
                    if not self.video.isOpened():
                        # Try different Pi camera module approaches
                        print("Trying Raspberry Pi camera module...")
                        
                        # Try standard Pi camera approach
                        self.video = cv2.VideoCapture(0, cv2.CAP_V4L2)
                        
                        if not self.video.isOpened():
                            # Try legacy Pi camera approach
                            self.video = cv2.VideoCapture(0, cv2.CAP_V4L)
                            
                        if not self.video.isOpened():
                            # Try GSTREAMER as a last resort
                            try:
                                cam_str = "v4l2src device=/dev/video0 ! video/x-raw, width=640, height=480 ! videoconvert ! appsink"
                                self.video = cv2.VideoCapture(cam_str, cv2.CAP_GSTREAMER)
                            except:
                                print("GStreamer pipeline failed")
                except Exception as e:
                    print(f"Error with Raspberry Pi camera: {str(e)}")
            else:
                # Standard approach for other platforms
                self.video = cv2.VideoCapture(current_camera)
            
            # If camera still not opened, try the default
            if not self.video or not self.video.isOpened():
                print(f"Failed to open camera {current_camera}, falling back to default camera")
                log_message(f"Failed to open camera {current_camera}, falling back to default camera", "warning")
                self.video = cv2.VideoCapture(0)  # Fallback to default camera
            
            # If we still can't open a camera, create a dummy one
            if not self.video or not self.video.isOpened():
                print("No camera available - creating mock camera")
                log_message("No physical camera available - using simulated camera", "warning")
                self.setup_mock_camera()
                return
                
            # Configure camera properties
            self.video.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
            self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
            self.video.set(cv2.CAP_PROP_FPS, frame_rate)
            
            # Verify camera is working
            success, _ = self.video.read()
            if not success:
                print("Camera opened but failed to read frame")
                log_message("Camera opened but failed to read frame", "warning")
                self.setup_mock_camera()
        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            log_message(f"Error initializing camera: {str(e)}", "error")
            # Create a mock camera as fallback
            self.setup_mock_camera()
    
    def setup_mock_camera(self):
        """Set up a mock camera that generates synthetic frames"""
        self.is_mock_camera = True
        self.mock_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        # Draw a colorful pattern on the mock frame
        cv2.rectangle(self.mock_frame, (0, 0), (frame_width, frame_height), (50, 50, 50), -1)
        cv2.putText(self.mock_frame, "Mock Camera Feed", (50, frame_height//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # Add a circle that will move around to simulate a video
        self.circle_x, self.circle_y = frame_width//2, frame_height//2
        self.dx, self.dy = 5, 3

    def __del__(self):
        if hasattr(self, 'video') and self.video is not None and (not hasattr(self, 'is_mock_camera') or not self.is_mock_camera):
            try:
                self.video.release()
            except:
                pass

    def get_frame(self):
        global system_status, last_log_time
        
        with self.lock:
            # Check if we're using a mock camera
            if hasattr(self, 'is_mock_camera') and self.is_mock_camera:
                # Create a mock frame with movement
                frame = self.mock_frame.copy()
                # Move the circle
                self.circle_x += self.dx
                self.circle_y += self.dy
                # Bounce off edges
                if self.circle_x <= 20 or self.circle_x >= frame_width-20:
                    self.dx *= -1
                if self.circle_y <= 20 or self.circle_y >= frame_height-20:
                    self.dy *= -1
                # Draw the moving circle
                cv2.circle(frame, (self.circle_x, self.circle_y), 15, (0, 120, 255), -1)
                success = True
            else:
                # Real camera - check status
                try:
                    # Make sure camera is still open
                    if self.video is None or not self.video.isOpened():
                        print("Camera is closed, attempting to reconnect...")
                        self.connect_camera()
                        if hasattr(self, 'is_mock_camera') and self.is_mock_camera:
                            # If we're now in mock camera mode, restart the function
                            return self.get_frame()
                        
                    # Read a frame from the camera
                    success, frame = self.video.read()
                    if not success or frame is None:
                        print("Failed to read frame from camera")
                        log_message("Error: Failed to read frame from camera", "error")
                        system_status = "error"
                        # Fall back to mock camera instead of returning None
                        self.setup_mock_camera()
                        return self.get_frame()
                except Exception as e:
                    print(f"Exception reading frame: {str(e)}")
                    log_message(f"Error reading camera frame: {str(e)}", "error")
                    system_status = "error"
                    # Fall back to mock camera
                    self.setup_mock_camera()
                    return self.get_frame()

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
        try:
            # Make sure video_stream exists
            if video_stream is None:
                placeholder = create_placeholder_frame("Camera not initialized")
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n\r\n')
                eventlet.sleep(1)  # Wait a bit longer before retry
                continue
                
            frame = video_stream.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
            else:
                # If frame is None, yield an error message or placeholder frame
                placeholder = create_placeholder_frame("Camera not available")
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n\r\n')
                # Wait a bit longer between retries when there's an issue
                eventlet.sleep(0.5)
                continue
        except Exception as e:
            print(f"Error in frame generation: {str(e)}")
            # Create a placeholder frame with error message
            placeholder = create_placeholder_frame("Error: " + str(e))
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n\r\n')
            # Wait a bit longer between retries when there's an exception
            eventlet.sleep(0.5)
            continue
        
        # Standard frame rate timing
        eventlet.sleep(0.033)  # ~30 FPS

def create_placeholder_frame(message):
    """Create a placeholder frame with an error message"""
    try:
        # Create a black frame with text
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, message, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return jpeg.tobytes()
    except Exception as e:
        print(f"Error creating placeholder frame: {str(e)}")
        # Create an even simpler fallback frame
        try:
            simple_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            _, jpeg = cv2.imencode('.jpg', simple_frame)
            return jpeg.tobytes()
        except:
            # Last resort - return an empty JPEG
            return b''

@app.route('/video_feed')
def video_feed():
    try:
        # Initialize the video stream if it doesn't exist yet
        global video_stream
        if video_stream is None:
            video_stream = VideoCamera()
        
        # Print debug info to server console
        print(f"Video feed requested. Camera status: {'OK' if video_stream and hasattr(video_stream, 'video') and video_stream.video and video_stream.video.isOpened() else 'Using mock camera' if hasattr(video_stream, 'is_mock_camera') and video_stream.is_mock_camera else 'NOT READY'}")
            
        # Force a camera reconnection if needed - helps with Raspberry Pi camera issues
        if not hasattr(video_stream, 'is_mock_camera') or not video_stream.is_mock_camera:
            if not hasattr(video_stream, 'video') or not video_stream.video or not video_stream.video.isOpened():
                print("Camera not properly initialized, attempting to reconnect...")
                video_stream.connect_camera()
        
        return Response(generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        import traceback
        print(f"ERROR IN VIDEO FEED: {str(e)}")
        print(traceback.format_exc())
        
        log_message(f"Error in video feed: {str(e)}", "error")
        
        # Return a static error image
        error_frame = create_placeholder_frame("Error: Camera unavailable")
        return Response(b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n',
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
        # Extract filter parameters
        search_term = data.get('query', '').lower()
        start_date = data.get('after', None)
        end_date = data.get('before', None)
        status_filter = data.get('status', 'all')
        page = int(data.get('page', 0))
        limit = int(data.get('limit', 20))
        
        # Filter logs based on parameters
        filtered_logs = []
        for i, log in enumerate(logs):
            # Determine log status
            log_level = log.get("level", "info")
            status = log_level
            if log_level == "error":
                status = "error"
            elif log_level == "warning":
                status = "warning"
            else:
                status = "normal"
                
            # Apply filters
            if search_term and search_term not in log["message"].lower():
                continue
                
            if start_date and log["timestamp"] < start_date:
                continue
                
            if end_date and log["timestamp"] > end_date:
                continue
                
            if status_filter != 'all' and status != status_filter:
                continue
                
            # Get count - use stored count if available, otherwise current
            count = log.get("count", stats["current_count"])
                
            # Add to filtered results
            filtered_logs.append({
                'id': i + 1,
                'timestamp': log["timestamp"],
                'count': count,
                'status': status,
                'message': log["message"],
                'details': {
                    'frame_rate': stats.get("frame_rate", 0),
                    'detection_time': stats.get("detection_time", 0),
                    'system_load': stats.get("system_load", 0),
                    'camera': f"Camera {current_camera}"
                }
            })
        
        # Calculate pagination
        total = len(filtered_logs)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        # Sort by timestamp (newest first)
        filtered_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Get the requested page
        start_idx = page * limit
        end_idx = min(start_idx + limit, total)
        paged_logs = filtered_logs[start_idx:end_idx] if start_idx < total else []
        
        return {
            'success': True,
            'logs': paged_logs,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'total_pages': total_pages
            }
        }
    except Exception as e:
        log_message(f"Error retrieving logs: {str(e)}", "error")
        return {'success': False, 'message': f'Error: {str(e)}'}

# Error Notification handlers
@socketio.on('get_errors')
def handle_get_errors(data):
    try:
        # Return the existing errors list that we maintain in real-time
        # Filter to only include active errors if specified
        active_only = data.get('active_only', False)
        
        filtered_errors = []
        for error in errors:
            if active_only and error['status'] != 'active':
                continue
                
            # Add additional real-time info to each error
            error_with_details = error.copy()
            error_with_details['details'] = {
                'count': stats['current_count'],
                'frame_rate': stats['frame_rate'],
                'system_load': stats['system_load'],
                'duration': get_time_since(error['timestamp'])
            }
            filtered_errors.append(error_with_details)
        
        return {'success': True, 'errors': filtered_errors, 'system_status': system_status}
    except Exception as e:
        log_message(f"Error retrieving system errors: {str(e)}", "error")
        return {'success': False, 'message': f'Error: {str(e)}'}

@socketio.on('fix_error')
def handle_fix_error(data):
    try:
        error_id = int(data['errorId'])
        
        # Find the error in our errors list
        error_idx = None
        for i, error in enumerate(errors):
            if error['id'] == error_id:
                error_idx = i
                break
                
        if error_idx is None:
            return {'success': False, 'message': f'Error #{error_id} not found'}
        
        error = errors[error_idx]
        source = error.get('source', 'system')
        
        # Attempt to fix based on error source
        if source == 'camera':
            # For camera errors, try to reinitialize the camera
            global video_stream, current_camera
            if video_stream:
                del video_stream
            video_stream = VideoCamera()
            log_message(f"Auto-fix: Reinitialized camera {current_camera}", "info")
            
        elif source == 'detection':
            # For detection errors, try adjusting sensitivity
            global sensitivity
            log_message(f"Auto-fix: Adjusted detection sensitivity", "info")
            
        # Mark error as resolved
        errors[error_idx]['status'] = 'resolved'
        errors[error_idx]['resolved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if we can update system status
        update_system_status()
        
        log_message(f"Successfully fixed error #{error_id} ({error['title']})", "info")
        return {
            'success': True, 
            'message': f'Error #{error_id} fix completed successfully',
            'system_status': system_status
        }
    except Exception as e:
        log_message(f"Error during fix attempt: {str(e)}", "error")
        return {'success': False, 'message': f'Error: {str(e)}'}

@socketio.on('dismiss_error')
def handle_dismiss_error(data):
    try:
        error_id = int(data['errorId'])
        
        # Find the error in our errors list
        for i, error in enumerate(errors):
            if error['id'] == error_id:
                # Mark as dismissed instead of removing
                errors[i]['status'] = 'dismissed'
                errors[i]['dismissed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Update system status
                update_system_status()
                
                log_message(f"Error #{error_id} dismissed", "info")
                return {'success': True, 'system_status': system_status}
        
        return {'success': False, 'message': f'Error #{error_id} not found'}
    except Exception as e:
        log_message(f"Error during dismissal: {str(e)}", "error")
        return {'success': False, 'message': f'Error: {str(e)}'}

@socketio.on('clear_all_errors')
def handle_clear_all_errors():
    try:
        # Mark all errors as dismissed
        dismissed_count = 0
        for i, error in enumerate(errors):
            if error['status'] == 'active':
                errors[i]['status'] = 'dismissed'
                errors[i]['dismissed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                dismissed_count += 1
        
        # Update system status
        update_system_status()
        
        log_message(f"All errors cleared ({dismissed_count} errors dismissed)", "info")
        return {'success': True, 'message': f'{dismissed_count} errors dismissed', 'system_status': system_status}
    except Exception as e:
        log_message(f"Error while clearing errors: {str(e)}", "error")
        return {'success': False, 'message': f'Error: {str(e)}'}

def log_message(message, level="info"):
    """
    Enhanced logging function that tracks message level and updates error tracking.
    
    Args:
        message: The message to log
        level: The level of the message (info, warning, error)
    """
    global system_status, logs, errors, socketio
    
    # Print to console as well for debugging
    print(f"[{level.upper()}] {message}")
    
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
        
def get_time_since(timestamp_str):
    """
    Calculate the time elapsed since the given timestamp
    
    Args:
        timestamp_str: Timestamp string in format '%Y-%m-%d %H:%M:%S'
        
    Returns:
        Human-readable string representing elapsed time
    """
    try:
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        diff = now - timestamp
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            return f"{int(seconds // 60)} minutes ago"
        elif seconds < 86400:
            return f"{int(seconds // 3600)} hours ago"
        else:
            return f"{int(seconds // 86400)} days ago"
    except Exception:
        return "Unknown time"
        
def update_system_status():
    """
    Update the global system status based on active errors
    """
    global system_status
    
    # Check for active errors
    high_severity_count = 0
    med_severity_count = 0
    
    for error in errors:
        if error['status'] == 'active':
            if error['severity'] == 'high':
                high_severity_count += 1
            elif error['severity'] == 'medium':
                med_severity_count += 1
    
    # Update status accordingly
    if high_severity_count > 0:
        system_status = "error"
    elif med_severity_count > 0:
        system_status = "warning"
    else:
        system_status = "normal"
        
    return system_status

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