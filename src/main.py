import cv2
import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detector.yolo import YOLODetector
from src.counter.counter import PersonCounter
from src.utils.visualization import draw_results
from src.camera.fixed_camera_new import Camera
import time

def main():
    # Initialize components
    detector = YOLODetector()
    counter = PersonCounter()
    camera = Camera(camera_id=0)
    
    # Performance tracking
    frame_time = time.time()
    fps = 0
    fps_display_interval = 30  # Update FPS display every 30 frames
    frame_count = 0
    
    try:
        while True:
            # Get frame from camera
            frame_bytes = camera.get_frame()
            if frame_bytes is None:
                continue
            
            # Convert JPEG bytes to frame
            try:
                frame_buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_buffer, cv2.IMREAD_COLOR)
                if frame is None or frame.size == 0:
                    continue
            except Exception as e:
                print(f"Error decoding frame: {e}")
                continue
            
            # Process frame
            try:
                # Update FPS calculation
                frame_count += 1
                if frame_count % fps_display_interval == 0:
                    current_time = time.time()
                    fps = fps_display_interval / (current_time - frame_time)
                    frame_time = current_time
                
                # Run detection
                detections = detector.detect(frame)
                
                # Update counter
                count = counter.update(detections)
                
                # Draw results and FPS
                output_frame = draw_results(frame, detections, count)
                cv2.putText(output_frame, f"FPS: {fps:.1f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Display result
                cv2.imshow('Person Counter', output_frame)
                
            except Exception as e:
                print(f"Error processing frame: {e}")
                continue
            
            # Check for exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()