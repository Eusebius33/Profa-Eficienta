import random

class ExerciseRegistry:
    def __init__(self):
        # Maps slot index (1 to 10) to a list of generator functions/classes
        self.slots = {i: [] for i in range(1, 11)}
        
    def register(self, slot: int):
        def decorator(func):
            # Attach slot attribute to the function for metadata inspection
            func.slot = slot
            # Ensure we don't register duplicates
            if func not in self.slots[slot]:
                self.slots[slot].append(func)
            return func
        return decorator

    def get_generators(self, slot: int) -> list:
        return self.slots.get(slot, [])

registry = ExerciseRegistry()
