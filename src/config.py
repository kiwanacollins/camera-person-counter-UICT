# Configuration settings for the camera person counter system

# Path to the YOLO model weights
YOLO_MODEL_PATH = "models/yolo_weights.h5"

# Path to the YOLO configuration file
YOLO_CONFIG_PATH = "models/yolo_config.cfg"

# Detection threshold for YOLO
DETECTION_THRESHOLD = 0.5

# Minimum confidence for counting a person
COUNTING_CONFIDENCE = 0.6

# Camera settings
CAMERA_RESOLUTION = (640, 480)
FRAME_RATE = 30

# Configuration parameters
CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4
WEBCAM_INDEX = 0