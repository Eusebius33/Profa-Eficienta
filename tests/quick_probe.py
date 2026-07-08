import sys
sys.path.insert(0, '.')
import logging
logging.basicConfig(level=logging.WARNING)
from bac_generator.generator import BACExamGenerator
import time

gen = BACExamGenerator()
results = []

for i in range(100):
    t0 = time.perf_counter()
    e = gen.generate_exam(seed=i*7)
    elapsed = time.perf_counter() - t0
    m = e.get('metadata', {})
    results.append((m.get('validation_status', '?'), m.get('attempts_required', 1), m.get('diversity_score', 0), elapsed))

success = sum(1 for r in results if r[0] == 'verified')
fallback = sum(1 for r in results if r[0] != 'verified')
avg_att = sum(r[1] for r in results) / len(results)
avg_div = sum(r[2] for r in results) / len(results)
avg_t   = sum(r[3] for r in results) / len(results)

print(f"100 exams: success={success} fallback={fallback}")
print(f"avg_attempts={avg_att:.1f} avg_diversity={avg_div:.3f} avg_time={avg_t:.3f}s")
print(f"dup_rejections={gen.stats['duplicate_rejections']}  val_failures={gen.stats['validation_failures']}")
