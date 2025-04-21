# Configuration settings for the camera person counter system

# YOLO model settings
YOLO_MODEL_PATH = "models/yolov4-tiny.weights"
YOLO_CONFIG_PATH = "models/yolov4-tiny.cfg"
DETECTION_THRESHOLD = 0.4  # Lowered from 0.5 to improve detection rate
CONFIDENCE_THRESHOLD = 0.4  # Lowered from 0.5
NMS_THRESHOLD = 0.3  # Lowered from 0.4 to reduce overlapping detections

# Camera settings - reduced resolution for better performance
CAMERA_RESOLUTION = (480, 360)  # Reduced from 640x480
FRAME_RATE = 15  # Reduced from 30 for better processing performance

# Additional performance settings
WEBCAM_INDEX = 0
ENABLE_HARDWARE_ACCELERATION = True
PROCESS_EVERY_N_FRAMES = 2  # Process every 2nd frame
MAX_DETECTION_FPS = 15  # Cap detection processing rate