import cv2
import numpy as np
import time
import subprocess
import glob
import os
import sys

class Camera:
    @staticmethod
    def check_device_exists(device_path):
        """Check if a device file exists and is accessible"""
        try:
            # Just try to open the device file for reading
            with open(device_path, 'rb') as f:
                return True
        except:
            return False
    
    @staticmethod
    def list_available_cameras():
        """List all available video devices using a more reliable method"""
        available_cameras = []
        devices_checked = set()
        
        # Get all video devices from /dev
        devices = glob.glob('/dev/video*')
        print(f"Found video devices: {devices}")
        
        # Test if we can even access video0 without using OpenCV
        primary_device = '/dev/video0'
        if primary_device in devices and Camera.check_device_exists(primary_device):
            # Try to open it without causing OpenCV warnings
            try:
                # Redirect stderr temporarily to suppress OpenCV warnings
                old_stderr = sys.stderr
                sys.stderr = open(os.devnull, 'w')
                
                try:
                    # Try to open the camera with index 0 (typically maps to video0)
                    cap = cv2.VideoCapture(0)
                    if cap.isOpened():
                        # Just add it without trying to read a frame
                        available_cameras.append(primary_device)
                        cap.release()
                        devices_checked.add(primary_device)
                        # Don't print success message here to reduce output
                except:
                    pass
                
                # Restore stderr
                sys.stderr.close()
                sys.stderr = old_stderr
                
            except:
                # If anything goes wrong with stderr redirection, continue quietly
                pass
        
        # If we found video0 and it works, just return that
        if primary_device in available_cameras:
            print(f"Using primary camera: {primary_device}")
            return available_cameras
            
        # Check only first three cameras to avoid too many warnings
        for device in devices[:3]:
            if device in devices_checked:
                continue
                
            # Just check if the device exists in /dev
            if Camera.check_device_exists(device):
                available_cameras.append(device)
                devices_checked.add(device)
        
        # If we still don't have any cameras, try indices 0-2 directly
        if not available_cameras:
            # This is a last resort - don't actually open with OpenCV here
            for i in range(3):
                device_path = f"/dev/video{i}"
                if Camera.check_device_exists(device_path) and device_path not in devices_checked:
                    available_cameras.append(device_path)
                    devices_checked.add(device_path)
        
        # Return whatever cameras we found, may be empty
        if available_cameras:
            print(f"Found camera device(s): {available_cameras}")
        else:
            print("No camera devices could be found or accessed")
        
        return available_cameras

    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.device_path = f"/dev/video{camera_id}"
        self.camera = None
        self.is_running = False
        self.backup_index = 0  # Fallback to index 0 if device path fails
        
        # Check if device exists before even trying to use it
        device_exists = os.path.exists(self.device_path)
        
        # Try to find available cameras, but don't fail immediately if none found
        available_cameras = self.list_available_cameras()
        
        # If no cameras are found but the requested device exists
        if not available_cameras and device_exists:
            print(f"Warning: Camera device {self.device_path} exists but may be in use.")
            print(f"Will attempt to use it directly during start_camera().")
        # If no cameras are found and the requested device doesn't exist
        elif not available_cameras and not device_exists:
            print(f"Warning: No camera devices found and {self.device_path} doesn't exist.")
            print("Will try fallback methods during start_camera().")
        # If the requested camera isn't in the available list but others are
        elif self.device_path not in available_cameras and available_cameras:
            print(f"Warning: Requested camera {self.device_path} not in available list")
            print(f"Will try requested camera first, then fall back to {available_cameras[0]}")
            self.backup_device = available_cameras[0]
    
    def start_camera(self):
        if self.is_running:
            return
            
        print(f"Attempting to open camera device {self.device_path}")
        
        # First attempt - try with the requested device path
        self.camera = None
        try:
            self.camera = cv2.VideoCapture(self.device_path)
            if self.camera.isOpened():
                print(f"Successfully opened camera with device path: {self.device_path}")
                self._configure_camera()
                self.is_running = True
                return
        except Exception as e:
            print(f"Failed to open camera with device path: {str(e)}")
            if self.camera:
                self.camera.release()
                self.camera = None
        
        # Second attempt - try with the camera index
        try:
            print(f"Trying to open camera with index: {self.camera_id}")
            self.camera = cv2.VideoCapture(self.camera_id)
            if self.camera.isOpened():
                print(f"Successfully opened camera with index: {self.camera_id}")
                self._configure_camera()
                self.is_running = True
                return
        except Exception as e:
            print(f"Failed to open camera with index: {str(e)}")
            if self.camera:
                self.camera.release()
                self.camera = None
        
        # Third attempt - try with backup device if available
        if hasattr(self, 'backup_device'):
            try:
                print(f"Trying backup camera: {self.backup_device}")
                self.camera = cv2.VideoCapture(self.backup_device)
                if self.camera.isOpened():
                    print(f"Successfully opened backup camera: {self.backup_device}")
                    self._configure_camera()
                    self.is_running = True
                    return
            except Exception as e:
                print(f"Failed to open backup camera: {str(e)}")
                if self.camera:
                    self.camera.release()
                    self.camera = None
        
        # Last resort - just try index 0
        try:
            print("Last resort: trying camera index 0")
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                print("Successfully opened camera at index 0")
                self._configure_camera()
                self.is_running = True
                return
        except Exception as e:
            print(f"Failed to open camera at index 0: {str(e)}")
            if self.camera:
                self.camera.release()
                self.camera = None
        
        # If we get here, all attempts failed
        raise RuntimeError("Could not open any camera after multiple attempts")
    
    def _configure_camera(self):
        """Configure camera settings if camera is open"""
        if not self.camera or not self.camera.isOpened():
            return False
            
        try:
            # Set a smaller resolution to start with
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # Try to read a test frame but don't raise exception if it fails
            ret, frame = self.camera.read()
            if not ret:
                print("Warning: Could not read test frame from camera")
                return False
                
            return True
        except Exception as e:
            print(f"Warning: Could not configure camera: {str(e)}")
            return False
    
    def capture_frame(self):
        if not self.is_running:
            try:
                self.start_camera()
            except Exception as e:
                print(f"Failed to start camera for capture: {e}")
                return False, None
        
        if not self.camera:
            return False, None
        
        try:
            success, frame = self.camera.read()
            if not success:
                print(f"Failed to capture frame")
                # Try to recover by restarting the camera
                try:
                    self.stop_camera()
                    time.sleep(1)
                    self.start_camera()
                    success, frame = self.camera.read()
                except Exception:
                    pass
                    
                if not success:
                    return False, None
            return True, frame
        except Exception as e:
            print(f"Error capturing frame: {str(e)}")
            return False, None
    
    def stop_camera(self):
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                print(f"Error releasing camera: {e}")
            self.camera = None
            self.is_running = False
            print("Camera stopped")
    
    def __del__(self):
        self.stop_camera()
