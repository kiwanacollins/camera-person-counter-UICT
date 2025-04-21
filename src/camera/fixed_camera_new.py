# filepath: /Users/kiwana/Desktop/camera-person-counter/src/camera/fixed_camera_new.py
import cv2
import numpy as np
from datetime import datetime

class Camera:
    def __init__(self, camera_id=0, frame_width=640, frame_height=480, frame_rate=30):
        self.camera_id = camera_id
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.frame_rate = frame_rate
        self.video = None
        self.is_mock_camera = False
        self.setup_camera()
        
        # Stats tracking
        self.frame_count = 0
        self.fps_start_time = datetime.now()
        self.actual_fps = 0
        
        # Mock camera variables
        self.circle_x, self.circle_y = frame_width//2, frame_height//2
        self.dx, self.dy = 5, 3
        self.mock_frame = None
    
    def setup_camera(self):
        """Initialize the real camera or fall back to a mock camera"""
        try:
            self.video = cv2.VideoCapture(self.camera_id)
            if self.video.isOpened():
                self.video.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.video.set(cv2.CAP_PROP_FPS, self.frame_rate)
                
                # Verify camera is working by reading a test frame
                success, _ = self.video.read()
                if not success:
                    print("Camera opened but failed to read test frame")
                    self.setup_mock_camera()
            else:
                print(f"Failed to open camera {self.camera_id}")
                self.setup_mock_camera()
        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            self.setup_mock_camera()
    
    def setup_mock_camera(self):
        """Set up a mock camera that generates synthetic frames"""
        self.is_mock_camera = True
        self.mock_frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        # Draw a colorful pattern on the mock frame
        cv2.rectangle(self.mock_frame, (0, 0), (self.frame_width, self.frame_height), (50, 50, 50), -1)
        cv2.putText(self.mock_frame, "Mock Camera Feed", (50, self.frame_height//2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    def get_frame(self):
        """
        Get a frame from the camera or generate a mock frame.
        Returns bytes of a JPEG image.
        """
        # This is the key fix - ensure we're returning bytes, not a function reference
        try:
            frame = None
            
            # Check if we're using a mock camera
            if self.is_mock_camera and self.mock_frame is not None:
                # Create a mock frame with movement
                frame = self.mock_frame.copy()
                # Move the circle
                self.circle_x += self.dx
                self.circle_y += self.dy
                # Bounce off edges
                if self.circle_x <= 20 or self.circle_x >= self.frame_width-20:
                    self.dx *= -1
                if self.circle_y <= 20 or self.circle_y >= self.frame_height-20:
                    self.dy *= -1
                # Draw the moving circle
                cv2.circle(frame, (self.circle_x, self.circle_y), 15, (0, 120, 255), -1)
            else:
                # Real camera - check status
                if self.video is not None and self.video.isOpened():
                    # Read a frame from the camera
                    success, frame = self.video.read()
                    if not success or frame is None:
                        print("Failed to read frame from camera")
                        # Fall back to mock camera
                        self.setup_mock_camera()
                        if self.mock_frame is not None:
                            frame = self.mock_frame.copy()
                            cv2.circle(frame, (self.circle_x, self.circle_y), 15, (0, 120, 255), -1)
                else:
                    print("Camera is closed, attempting to reconnect...")
                    self.setup_camera()
                    if self.is_mock_camera and self.mock_frame is not None:
                        frame = self.mock_frame.copy()
                        cv2.circle(frame, (self.circle_x, self.circle_y), 15, (0, 120, 255), -1)

            # Update stats
            self.update_stats()
            
            # Encode the frame
            if frame is not None and isinstance(frame, np.ndarray) and frame.size > 0:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                return jpeg.tobytes()  # Ensure we return bytes, not a function reference
            else:
                # Create a simple error frame if frame is invalid
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, "No valid frame", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                _, jpeg = cv2.imencode('.jpg', error_frame)
                return jpeg.tobytes()  # Ensure we return bytes, not a function reference
        except Exception as e:
            print(f"Error in get_frame: {str(e)}")
            # Create an error frame
            try:
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, f"Error: {str(e)}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                _, jpeg = cv2.imencode('.jpg', error_frame)
                return jpeg.tobytes()  # Ensure we return bytes, not a function reference
            except:
                # Last resort - return an empty JPEG that still has length
                return b'EMPTY_FRAME'  # This is a fix to prevent "has no len()" errors
    
    def update_stats(self):
        """Update frame statistics including FPS calculation"""
        current_time = datetime.now()
        self.frame_count += 1
        
        # Calculate actual FPS every second
        time_diff = (current_time - self.fps_start_time).total_seconds()
        if time_diff >= 1.0:
            self.actual_fps = self.frame_count / time_diff
            self.frame_count = 0
            self.fps_start_time = current_time
            
            # Log warnings for low FPS
            if self.actual_fps < (self.frame_rate * 0.7) and self.actual_fps > 0:
                print(f"Warning: Low frame rate detected ({self.actual_fps:.1f} FPS)")
            
            # Check system load
            try:
                # This is a simple heuristic - if FPS is much lower than target, assume high system load
                if self.actual_fps < (self.frame_rate * 0.5):
                    print("[WARNING] Warning: High system load detected")
            except:
                pass
    
    def __del__(self):
        """Release the camera when the object is deleted"""
        if self.video is not None and not self.is_mock_camera:
            try:
                self.video.release()
            except:
                pass
