import cv2
import numpy as np
import time
import subprocess
import glob
import os
import fcntl  # Add fcntl for file locking checks

class Camera:
    @staticmethod
    def check_device_accessible(device_path):
        """Check if a device is accessible without actually opening it with OpenCV"""
        try:
            # Try to open the device file directly to see if we have permission
            with open(device_path, 'rb') as f:
                # Try to get exclusive access to check if it's in use
                try:
                    # Use LOCK_EX | LOCK_NB for non-blocking exclusive lock
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # If we get here, the file isn't locked by another process
                    fcntl.flock(f, fcntl.LOCK_UN)
                    return True
                except IOError:
                    # Device is locked by another process
                    return False
        except (IOError, PermissionError):
            # Can't open the device at all
            return False
        return True

    @staticmethod
    def list_available_cameras():
        """List all available video devices"""
        available_cameras = []
        
        # First try reading from /dev/video*
        devices = glob.glob('/dev/video*')
        print(f"Found video devices: {devices}")
        
        # First check if devices are accessible without trying to open them with OpenCV
        for device in devices:
            if Camera.check_device_accessible(device):
                available_cameras.append(device)
                print(f"Found accessible camera device: {device}")
                # If we found /dev/video0 and it's accessible, just use that one
                if device == '/dev/video0':
                    return [device]
        
        # If we found some accessible cameras, return those
        if available_cameras:
            print(f"Using accessible camera(s): {available_cameras}")
            return available_cameras
            
        # If no accessible cameras found, try a more aggressive approach
        # Try direct numeric indices without accessing /dev/video* paths
        for i in range(3):  # Try the first 3 indices
            try:
                # Redirect stderr to avoid OpenCV warnings
                stderr_fd = os.dup(2)
                null_fd = os.open(os.devnull, os.O_RDWR)
                os.dup2(null_fd, 2)
                
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            available_cameras.append(f"/dev/video{i}")
                    cap.release()
                finally:
                    # Restore stderr
                    os.dup2(stderr_fd, 2)
                    os.close(stderr_fd)
                    os.close(null_fd)
            except Exception:
                # Silently ignore errors
                pass
        
        # If we found cameras with the numeric index approach
        if available_cameras:
            print(f"Found cameras using direct indices: {available_cameras}")
            
        return available_cameras

    def __init__(self, camera_id=0, force=False):
        self.camera_id = camera_id
        self.device_path = f"/dev/video{camera_id}"
        self.camera = None
        self.is_running = False
        self.force = force  # Add force option to bypass some checks
        
        # Try to find available cameras
        available_cameras = self.list_available_cameras()
        if not available_cameras:
            # Try to fix permission issues
            if os.path.exists(self.device_path):
                print(f"Camera device {self.device_path} exists but cannot be accessed.")
                print("Trying alternative access methods...")
                # If force is enabled, we'll try to open it directly later
                if not self.force:
                    raise RuntimeError(f"Camera device {self.device_path} exists but cannot be opened. It might be in use by another application.")
            else:
                raise RuntimeError("No cameras found. Please check if your camera is properly connected.")
        
        # If the requested camera isn't available but others are, use the first available one
        if not self.force and self.device_path not in available_cameras and available_cameras:
            print(f"Warning: Requested camera {self.device_path} not available")
            self.device_path = available_cameras[0]
            print(f"Using camera {self.device_path} instead")
    
    def start_camera(self):
        if not self.is_running:
            print(f"Opening camera device {self.device_path}")
            try:
                # Try a few different methods to open the camera
                success = False
                
                # First try with direct device path
                if not success:
                    try:
                        self.camera = cv2.VideoCapture(self.device_path)
                        if self.camera.isOpened():
                            success = True
                    except Exception as e:
                        print(f"Failed to open with device path: {e}")
                
                # Try with device index
                if not success:
                    try:
                        self.camera = cv2.VideoCapture(self.camera_id)
                        if self.camera.isOpened():
                            success = True
                    except Exception as e:
                        print(f"Failed to open with device index: {e}")
                
                # If both methods failed, try with MJPG format explicitly
                if not success and self.force:
                    try:
                        self.camera = cv2.VideoCapture(self.camera_id)
                        self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
                        if self.camera.isOpened():
                            success = True
                    except Exception as e:
                        print(f"Failed to open with MJPG format: {e}")
                
                if not success:
                    if self.force:
                        print("WARNING: Camera could not be initialized properly but continuing due to force=True")
                        self.camera = cv2.VideoCapture(0)  # Last resort - try index 0
                        self.is_running = True
                        return
                    else:
                        raise RuntimeError(f"Could not open camera at {self.device_path} or index {self.camera_id}")
                
                # Set a smaller resolution to start with
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                
                # Try to read a test frame
                ret, frame = self.camera.read()
                if not ret and not self.force:
                    raise RuntimeError("Could not read frame from camera")
                
                self.is_running = True
                print("Camera started successfully")
            except Exception as e:
                print(f"Error starting camera: {str(e)}")
                if self.camera:
                    self.camera.release()
                    self.camera = None
                raise
    
    def capture_frame(self):
        if not self.is_running:
            self.start_camera()
        
        try:
            success, frame = self.camera.read()
            if not success:
                print(f"Failed to capture frame from {self.device_path}")
                # Try to recover
                self.stop_camera()
                time.sleep(1)
                self.start_camera()
                success, frame = self.camera.read()
                if not success:
                    return False, None
            return True, frame
        except Exception as e:
            print(f"Error capturing frame: {str(e)}")
            return False, None
    
    def stop_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
            self.is_running = False
            print("Camera stopped")
    
    def __del__(self):
        self.stop_camera()