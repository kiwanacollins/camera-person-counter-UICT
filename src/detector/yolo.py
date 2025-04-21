import cv2
import numpy as np
import sys
import os
# Import Sequence for type hinting
from collections.abc import Sequence 

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
        
        # Robustly get output layer names regardless of OpenCV version
        try:
            output_layers_indices = self.net.getUnconnectedOutLayers()
            # Case 1: Indices are wrapped in a NumPy array (e.g., [[200], [227]])
            if isinstance(output_layers_indices, np.ndarray) and output_layers_indices.ndim > 1:
                 self.output_layers = [self.layer_names[i[0] - 1] for i in output_layers_indices]
            # Case 2: Indices are plain integers in a list or tuple (e.g., (200, 227))
            elif isinstance(output_layers_indices, (list, tuple)):
                 self.output_layers = [self.layer_names[i - 1] for i in output_layers_indices]
            # Case 3: A single integer index is returned
            elif isinstance(output_layers_indices, int):
                 self.output_layers = [self.layer_names[output_layers_indices - 1]]
            else:
                 # Fallback or error handling if the format is unexpected
                 print(f"Warning: Unexpected format for getUnconnectedOutLayers(): {type(output_layers_indices)}. Attempting default.")
                 # Attempt a common default if unsure (may need adjustment)
                 self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]

        except Exception as e:
            print(f"Error determining output layers: {e}. Falling back to manual specification (may be incorrect).")
            # Provide a fallback if auto-detection fails completely
            # These might need adjustment based on the specific yolov4-tiny version
            self.output_layers = ['yolo_30', 'yolo_37'] 

    def detect(self, frame, confidence_threshold=None):
        """
        Detect objects in the given frame
        Args:
            frame: The image frame to detect objects in
            confidence_threshold: Optional threshold to override default confidence
        Returns:
            list: A list of detection boxes [x, y, w, h]
        """
        # Ensure we always return a list
        try:
            if confidence_threshold is None:
                confidence_threshold = CONFIDENCE_THRESHOLD
            
            if frame is None:
                print("Warning: Received None frame")
                return []
                
            height, width = frame.shape[:2]
            
            # Create blob from image
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
            
            # Detect objects - fixed implementation to handle different OpenCV versions
            self.net.setInput(blob)
            try:
                # Try to forward all layers at once
                outs = self.net.forward(self.output_layers)
            except Exception as e:
                # Fall back to getting each layer individually if the grouped approach fails
                print(f"Forward pass error, trying alternative: {e}")
                outs = []
                for layer in self.output_layers:
                    try:
                        out = self.net.forward(layer)
                        outs.append(out)
                    except Exception as layer_err:
                        print(f"Error in layer {layer}: {layer_err}")
            
            # Initialize empty lists
            boxes = []
            confidences = []
            class_ids = []
            detections = []  # Final list to return
            
            # Process detections
            for out in outs:
                if not isinstance(out, np.ndarray):
                    continue
                    
                for detection in out:
                    if len(detection) < 85:  # YOLO output should have 85 values
                        continue
                        
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = float(scores[class_id])
                    
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
                        confidences.append(confidence)
                        class_ids.append(class_id)
            
            # Apply non-maximum suppression with instance threshold
            # Ensure boxes and confidences are lists before passing to NMSBoxes
            if not isinstance(boxes, list): boxes = []
            if not isinstance(confidences, list): confidences = []
            
            # Use the instance's NMS threshold
            nms_threshold = NMS_THRESHOLD 

            # Call NMSBoxes
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)

            detections = []
            # Check if indexes is not None and has items before processing
            # Handle tuple return type from NMSBoxes in some OpenCV versions
            if indexes is not None:
                 # Flatten if it's a multi-dimensional array
                 if isinstance(indexes, np.ndarray) and indexes.ndim > 1:
                     indexes_flat = indexes.flatten()
                 # Handle tuple case (often means empty result)
                 elif isinstance(indexes, tuple):
                     # If the tuple is not empty, assume it contains indices
                     if len(indexes) > 0:
                         indexes_flat = list(indexes) 
                     else:
                         indexes_flat = [] # Empty tuple means no boxes survived NMS
                 # Handle flat list/array case
                 elif isinstance(indexes, (list, np.ndarray)):
                      indexes_flat = indexes
                 # Handle single integer case (less common but possible)
                 elif isinstance(indexes, int):
                      indexes_flat = [indexes]
                 else:
                      print(f"Warning: Unexpected type for NMSBoxes result: {type(indexes)}")
                      indexes_flat = []

                 # Process the flattened indices
                 if len(indexes_flat) > 0:
                     for i in indexes_flat:
                         # Add bounds check for safety
                         if 0 <= i < len(boxes):
                             detections.append(boxes[i])
                         else:
                             print(f"Warning: NMS index {i} out of bounds for boxes list (len={len(boxes)})")

            # Final validation
            if not isinstance(detections, list):
                print(f"Warning: detections is type {type(detections)}, converting to list")
                try:
                    detections = list(detections)
                except:
                    detections = []
            
            return detections # Returns the list
        except Exception as e:
            print(f"Error in YOLODetector.detect: {e}")
            # Explicitly return empty list on error
            return []