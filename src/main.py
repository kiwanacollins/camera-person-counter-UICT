import cv2
import sys
import os
import numpy as np

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detector.yolo import YOLODetector
from src.counter.counter import PersonCounter
from src.utils.visualization import draw_results
from src.camera.fixed_camera import Camera
import time

def main():
    # Initialize components
    detector = YOLODetector()
    counter = PersonCounter()
    
    # Initialize the fixed camera implementation
    camera = Camera(camera_id=0)
    
    try:
        while True:
            # Get frame from the camera (returns JPEG bytes)
            jpeg_bytes = camera.get_frame()
            
            # Convert JPEG bytes back to a frame
            frame_buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_buffer, cv2.IMREAD_COLOR)
            
            if frame is None or frame.size == 0:
                print("Invalid frame received, skipping frame")
                continue
                
            # Detect persons
            detections = detector.detect(frame)
            
            # Count persons
            count = counter.update(detections)  # Changed from count() to update()
            
            # Draw results
            output_frame = draw_results(frame, detections, count)
            
            # Display result
            cv2.imshow('Person Counter', output_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        # Camera will be released automatically in __del__
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()