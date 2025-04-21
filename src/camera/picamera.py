import cv2
import numpy as np
import time
import subprocess
import glob
import os

class Camera:
    @staticmethod
    def list_available_cameras():
        """List all available video devices"""
        available_cameras = []
        
        # First try reading from /dev/video*
        devices = glob.glob('/dev/video*')
        print(f"Found video devices: {devices}")
        
        for device in devices:
            try:
                # Get device number
                device_num = int(device.replace('/dev/video', ''))
                
                # Try opening with device number first
                cap = cv2.VideoCapture(device_num)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        available_cameras.append(device)
                        print(f"Successfully opened camera {device}")
                    cap.release()
                    continue
                
                # If that fails, try opening with device path
                cap = cv2.VideoCapture(device)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        available_cameras.append(device)
                        print(f"Successfully opened camera {device}")
                    cap.release()
            except Exception as e:
                print(f"Error testing device {device}: {str(e)}")
                continue
        
        if not available_cameras:
            # Try a few index numbers directly as a fallback
            for i in range(4):
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            available_cameras.append(f"/dev/video{i}")
                            print(f"Found camera at index {i}")
                        cap.release()
                except Exception as e:
                    print(f"Error testing camera index {i}: {str(e)}")
        
        print(f"Available cameras: {available_cameras}")
        return available_cameras

    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.device_path = f"/dev/video{camera_id}"
        self.camera = None
        self.is_running = False
        
        # Try to find available cameras
        available_cameras = self.list_available_cameras()
        if not available_cameras:
            # Check if the camera device exists but might be in use
            if os.path.exists(self.device_path):
                raise RuntimeError(f"Camera device {self.device_path} exists but cannot be opened. It might be in use by another application.")
            raise RuntimeError("No cameras found. Please check if your camera is properly connected and not in use by another application.")
        
        # If the requested camera isn't available, use the first available one
        if self.device_path not in available_cameras:
            print(f"Warning: Requested camera {self.device_path} not available")
            self.device_path = available_cameras[0]
            print(f"Using camera {self.device_path} instead")
    
    def start_camera(self):
        if not self.is_running:
            print(f"Opening camera device {self.device_path}")
            try:
                # Try opening with direct device path first
                self.camera = cv2.VideoCapture(self.device_path)
                if not self.camera.isOpened():
                    # If that fails, try with device number
                    self.camera = cv2.VideoCapture(self.camera_id)
                    if not self.camera.isOpened():
                        raise RuntimeError(f"Could not open camera at {self.device_path} or index {self.camera_id}")
                
                # Set a smaller resolution to start with
                if not self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640):
                    print("Warning: Could not set width to 640")
                if not self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480):
                    print("Warning: Could not set height to 480")
                if not self.camera.set(cv2.CAP_PROP_FPS, 30):
                    print("Warning: Could not set FPS to 30")
                
                # Try to read a test frame
                ret, frame = self.camera.read()
                if not ret:
                    raise RuntimeError("Could not read frame from camera")
                
                self.is_running = True
                print("Camera started successfully")
            except Exception as e:
                print(f"Error starting camera: {str(e)}")
                if self.camera:
                    self.camera.release()
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
        if self.is_running and self.camera:
            self.camera.release()
            self.is_running = False
            print("Camera stopped")
    
    def __del__(self):
        self.stop_camera()