import cv2
import numpy as np
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CONFIDENCE_THRESHOLD, NMS_THRESHOLD

class YOLODetector:
    def __init__(self):
        # Load YOLO network
        self.net = cv2.dnn.readNet(
            "models/yolov4-tiny.weights",
            "models/yolov4-tiny.cfg"
        )
        
        # Load classes
        with open("models/coco.names", "r") as f:
            self.classes = [line.strip() for line in f.readlines()]
        
        self.layer_names = self.net.getLayerNames()
        output_layers_indices = self.net.getUnconnectedOutLayers()
        
        # Fix for OpenCV versions compatibility
        if isinstance(output_layers_indices[0], np.ndarray):
            self.output_layers = [self.layer_names[i[0] - 1] for i in output_layers_indices]
        else:
            self.output_layers = [self.layer_names[i - 1] for i in output_layers_indices]
        
    def detect(self, frame, confidence_threshold=None):
        """
        Detect objects in the given frame
        Args:
            frame: The image frame to detect objects in
            confidence_threshold: Optional threshold to override default confidence
        """
        if confidence_threshold is None:
            confidence_threshold = CONFIDENCE_THRESHOLD
            
        height, width = frame.shape[:2]
        
        # Create blob from image
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
        
        # Detect objects
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)
        
        # Information to display on screen
        boxes = []
        confidences = []
        class_ids = []
        
        # Showing information on the screen
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > confidence_threshold and class_id == 0:  # 0 is person class
                    # Object detected
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # Rectangle coordinates
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Apply non-maximum suppression
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, NMS_THRESHOLD) if boxes else []
        
        detections = []
        if indexes and len(indexes) > 0:
            # Handle different return types from NMSBoxes in different OpenCV versions
            if isinstance(indexes, np.ndarray):
                indexes = indexes.flatten()
            
            for i in indexes:
                detections.append(boxes[i])
        
        # Make sure we return a list, not a function
        return list(detections)