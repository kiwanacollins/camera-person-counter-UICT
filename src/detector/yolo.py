import cv2
import numpy as np
import sys
import os
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
        
        # Try OpenCL acceleration as fallback if CUDA is not available
        try:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            print("CUDA backend enabled for YOLO detection")
        except:
            try:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
                print("OpenCL acceleration enabled for YOLO detection")
            except:
                print("Hardware acceleration not available, using CPU")
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        
        # Load classes
        with open("models/coco.names", "r") as f:
            self.classes = [line.strip() for line in f.readlines()]
        
        self.layer_names = self.net.getLayerNames()
        self.output_layers = self._get_output_layers()
        
        # Cache parameters - use smaller input size for better performance
        self.input_size = (320, 320)  # Reduced from 416x416
        self.scale = 1/255.0
        self.last_blob = None
        self.last_frame_shape = None
        self.frame_count = 0
        self.process_every_n_frames = 2  # Process every 2nd frame

    def _get_output_layers(self):
        """Get output layers robustly across different OpenCV versions"""
        try:
            output_layers_indices = self.net.getUnconnectedOutLayers()
            
            # Handle different return types
            if isinstance(output_layers_indices, np.ndarray):
                if output_layers_indices.ndim > 1:
                    indices = [i[0] - 1 for i in output_layers_indices]
                else:
                    indices = [i - 1 for i in output_layers_indices]
            else:
                indices = [i - 1 for i in output_layers_indices]
                
            return [self.layer_names[i] for i in indices]
            
        except Exception as e:
            print(f"Error determining output layers: {e}")
            # Provide fallback for YOLOv4-tiny
            return ['yolo_16', 'yolo_23']

    def _create_blob(self, frame):
        """Create input blob, reuse if frame size hasn't changed"""
        current_shape = frame.shape[:2]
        if (self.last_blob is None or 
            self.last_frame_shape != current_shape):
            
            # Resize frame to smaller size for faster processing
            resized = cv2.resize(frame, self.input_size)
            
            self.last_blob = cv2.dnn.blobFromImage(
                resized, 
                self.scale, 
                self.input_size, 
                swapRB=True, 
                crop=False
            )
            self.last_frame_shape = current_shape
            
        return self.last_blob

    def detect(self, frame, confidence_threshold=None):
        """
        Detect objects in the given frame
        Args:
            frame: The image frame to detect objects in
            confidence_threshold: Optional threshold to override default confidence
        Returns:
            list: A list of detection boxes [x, y, w, h]
        """
        # Skip frames to improve performance
        self.frame_count += 1
        if self.frame_count % self.process_every_n_frames != 0:
            return []
            
        if confidence_threshold is None:
            confidence_threshold = CONFIDENCE_THRESHOLD
            
        if frame is None or frame.size == 0:
            print("Warning: Received invalid frame")
            return []
            
        try:
            height, width = frame.shape[:2]
            
            # Create and set blob
            blob = self._create_blob(frame)
            self.net.setInput(blob)
            
            # Run forward pass
            outs = self.net.forward(self.output_layers)
            
            # Initialize lists for detections
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
                    
                    if confidence > confidence_threshold and class_id == 0:
                        # Scale coordinates back to original image size
                        scale_x = width / self.input_size[0]
                        scale_y = height / self.input_size[1]
                        
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        # Convert center coordinates to top-left
                        x = max(0, int(center_x - w/2))
                        y = max(0, int(center_y - h/2))
                        
                        boxes.append([x, y, w, h])
                        confidences.append(confidence)
            
            # Apply NMS
            if boxes:
                indices = cv2.dnn.NMSBoxes(
                    boxes, 
                    confidences, 
                    confidence_threshold, 
                    NMS_THRESHOLD
                )
                
                if isinstance(indices, np.ndarray):
                    indices = indices.flatten()
                
                return [boxes[i] for i in indices]
            
            return []
            
        except Exception as e:
            print(f"Error in YOLODetector.detect: {e}")
            return []