import sys; sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from bac_generator.duplicate.similarity import DuplicateDetector

d = DuplicateDetector()
print(f'Official exams pre-registered: {len(d.past_exams)}')
for i, pe in enumerate(d.past_exams):
    ids = pe["ids"]
    print(f'  Official exam {i+1} IDs: {ids}')
