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
            
            # Apply non-maximum suppression if we have detections
            if len(boxes) > 0:
                try:
                    indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, NMS_THRESHOLD)
                    
                    # Handle different return formats across OpenCV versions
                    if len(indexes) > 0:
                        # OpenCV 4.5.4+ returns a single-dimensional array
                        if isinstance(indexes, np.ndarray) and indexes.ndim == 1:
                            pass  # Already in the right format
                        # OpenCV 4.5.3 and earlier returns a 2D array
                        elif isinstance(indexes, np.ndarray) and indexes.ndim == 2:
                            indexes = indexes.flatten()
                        # Some versions might return a tuple
                        elif isinstance(indexes, tuple) and len(indexes) > 0:
                            indexes = indexes[0].flatten() if isinstance(indexes[0], np.ndarray) else indexes[0]
                    
                    # Process the indexes safely
                    if len(indexes) == 0:
                        # No detections after NMS
                        pass
                    elif isinstance(indexes, (int, np.integer)):
                        # Handle case where indexes might be a single integer
                        if 0 <= indexes < len(boxes):
                            detections.append(boxes[indexes])
                    else:
                        # Handle normal iterable case
                        for i in indexes:
                            if isinstance(i, (int, np.integer)) and 0 <= i < len(boxes):
                                detections.append(boxes[i])
                except Exception as e:
                    print(f"NMS failed: {e}, using all boxes")
                    detections = boxes.copy()  # Use copy to avoid reference issues
            
            # Final validation
            if not isinstance(detections, list):
                print(f"Warning: detections is type {type(detections)}, converting to list")
                try:
                    detections = list(detections)
                except:
                    detections = []
            
            return detections
            
        except Exception as e:
            print(f"Error in detect(): {e}")
            return []  # Always return a list, even on error