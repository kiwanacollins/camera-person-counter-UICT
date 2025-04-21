import cv2
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detector.yolo import YOLODetector
from src.counter.counter import PersonCounter
from src.utils.visualization import draw_results
import time

def main():
    # Initialize components
    detector = YOLODetector()
    counter = PersonCounter()
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
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
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()