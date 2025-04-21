import collections.abc # Import Sequence

class PersonCounter:
    def __init__(self):
        self.person_count = 0
        self.tracked_objects = {}
    
    def update(self, detections):
        # Update count based on detections
        # Add type check before calling len()
        if isinstance(detections, collections.abc.Sequence):
            self.person_count = len(detections)
        else:
            print(f"Warning: PersonCounter.update received unexpected type for detections: {type(detections)}. Setting count to 0.")
            self.person_count = 0
        return self.person_count

    def increment_count(self):
        self.person_count += 1

    def get_count(self):
        return self.person_count