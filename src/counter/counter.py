class PersonCounter:
    def __init__(self):
        self.person_count = 0
        self.tracked_objects = {}
    
    def update(self, detections):
        # Update count based on detections
        self.person_count = len(detections)
        return self.person_count

    def increment_count(self):
        self.person_count += 1

    def get_count(self):
        return self.person_count