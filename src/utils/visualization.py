import cv2

def draw_boxes(image, boxes, classes, scores):
    """
    Draw bounding boxes on the image for detected objects.
    
    Parameters:
        image: The image on which to draw the boxes.
        boxes: A list of bounding box coordinates.
        classes: A list of class labels for the detected objects.
        scores: A list of confidence scores for the detections.
    """
    for box, cls, score in zip(boxes, classes, scores):
        x1, y1, x2, y2 = box
        color = (0, 255, 0)  # Green color for the boxes
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        label = f"{cls}: {score:.2f}"
        cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def show_count(image, count):
    """
    Display the count of detected persons on the image.
    
    Parameters:
        image: The image on which to display the count.
        count: The count of detected persons.
    """
    cv2.putText(image, f"Count: {count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

def draw_results(frame, detections, count):
    # Draw bounding boxes
    for detection in detections:
        x, y, w, h = detection
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    # Draw count
    cv2.putText(frame, f'Count: {count}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    return frame