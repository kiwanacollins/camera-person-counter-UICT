import cv2
import numpy as np
import sys
import os
import time

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CONFIDENCE_THRESHOLD, NMS_THRESHOLD

class YOLODetector:
    def __init__(self):
        # Load YOLO network and weights
        try:
            self.net = cv2.dnn.readNet(
                "models/yolov4-tiny.weights",
                "models/yolov4-tiny.cfg"
            )
            print("Successfully loaded YOLO model")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            raise
        
        # Try hardware acceleration
        self._setup_hardware_acceleration()
        
        # Load classes
        with open("models/coco.names", "r") as f:
            self.classes = [line.strip() for line in f.readlines()]
        
        self.layer_names = self.net.getLayerNames()
        self.output_layers = self._get_output_layers()
        
        # Cache parameters for better performance
        self.input_size = (320, 320)  # Reduced from 416x416 for better speed
        self.scale = 1/255.0
        self.last_frame_shape = None
        
        # Performance tracking
        self.last_detection_time = 0
        self.frame_count = 0
        self.process_every_n_frames = 2
        
        # Initialize detection cache
        self.cached_detections = None
        self.detection_cache_ttl = 0.1  # 100ms cache lifetime
        
    def _setup_hardware_acceleration(self):
        """Try to enable hardware acceleration"""
        try:
            # Try CUDA first
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            print("Using CUDA acceleration")
            return
        except:
            try:
                # Try OpenCL as fallback
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
                print("Using OpenCL acceleration")
                return
            except:
                print("Hardware acceleration not available, using CPU")
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def _get_output_layers(self):
        """Get output layers robustly"""
        try:
            output_layers_indices = self.net.getUnconnectedOutLayers()
            
            if isinstance(output_layers_indices, np.ndarray):
                indices = output_layers_indices.flatten() - 1
            else:
                indices = [i - 1 for i in output_layers_indices]
                
            return [self.layer_names[i] for i in indices]
            
        except Exception as e:
            print(f"Error getting output layers: {e}")
            # Fallback for YOLOv4-tiny
            return ['yolo_16', 'yolo_23']

    def detect(self, frame, confidence_threshold=None):
        """
        Detect people in frame with caching for performance
        """
        current_time = time.time()
        
        # Use cached detections if they're fresh enough
        if (self.cached_detections is not None and 
            current_time - self.last_detection_time < self.detection_cache_ttl):
            return self.cached_detections
            
        # Skip frames to improve performance
        self.frame_count += 1
        if self.frame_count % self.process_every_n_frames != 0:
            return self.cached_detections if self.cached_detections is not None else []
        
        if confidence_threshold is None:
            confidence_threshold = CONFIDENCE_THRESHOLD
            
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            print("Warning: Invalid frame passed to detector")
            return []
            
        try:
            height, width = frame.shape[:2]
            
            # Prepare input blob
            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame, self.input_size),
                self.scale,
                self.input_size,
                swapRB=True,
                crop=False
            )
            
            self.net.setInput(blob)
            
            # Run detection
            outs = self.net.forward(self.output_layers)
            
            # Initialize detection lists
            boxes = []
            confidences = []
            
            # Process detections - only look for person class (index 0)
            for out in outs:
                for detection in out:
                    if len(detection) < 85:  # YOLO output should have 85 values
                        continue
                        
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = float(scores[class_id])
                    
                    # Only process person detections above threshold
                    if class_id == 0 and confidence > confidence_threshold:
                        # Scale coordinates back to original image size
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        # Calculate bounding box coordinates
                        x = max(0, int(center_x - w/2))
                        y = max(0, int(center_y - h/2))
                        
                        boxes.append([x, y, w, h])
                        confidences.append(confidence)
            
            # Apply non-maximum suppression
            if boxes:
                indices = cv2.dnn.NMSBoxes(
                    boxes,
                    confidences,
                    confidence_threshold,
                    NMS_THRESHOLD
                ).flatten()
                
                # Update cache
                self.cached_detections = [boxes[i] for i in indices]
                self.last_detection_time = current_time
                
                return self.cached_detections
            
            return []
            
        except Exception as e:
            print(f"Error in detection: {e}")
            return []