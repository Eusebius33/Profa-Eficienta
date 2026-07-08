"""
Stress test: Generate 1,000 BAC exams and report:
  - Duplicate rejection rate
  - Average regeneration attempts per exam
  - Diversity score distribution (min/mean/max/stddev)
  - Average generation time
  - Template coverage across all generated exams

Run from project root:
    python tests/stress_test.py
"""
import sys
import os
import time
import statistics

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bac_generator.generator import BACExamGenerator

def run_stress_test(n: int = 1000, threshold: float = 0.6):
    print("=" * 65)
    print(f"  BAC Generator Stress Test — {n} exams (threshold={threshold*100:.0f}%)")
    print("=" * 65)

    gen = BACExamGenerator()

    successes    = 0
    failures     = 0
    gen_times    = []
    attempts_per = []
    div_scores   = []
    template_usage: dict[str, int] = {}

    for i in range(1, n + 1):
        t0 = time.perf_counter()
        try:
            exam = gen.generate_exam(seed=i * 13, duplicate_threshold=threshold)
            elapsed = time.perf_counter() - t0
            gen_times.append(elapsed)

            meta = exam.get("metadata", {})
            status = meta.get("validation_status", "verified")
            div    = meta.get("diversity_score", 1.0)
            att    = meta.get("attempts_required", 1)

            if status == "fallback_max_attempts":
                failures += 1
            else:
                successes += 1

            div_scores.append(div)
            attempts_per.append(att)

            # Track template usage
            for fp in meta.get("exercise_fingerprints", []):
                tid = fp.get("template_id", fp.get("id", "?"))
                template_usage[tid] = template_usage.get(tid, 0) + 1

            if i % 100 == 0:
                avg_t = statistics.mean(gen_times[-100:]) if gen_times else 0
                print(f"  [{i:4d}/{n}]  success={successes}  fail={failures}  "
                      f"avg_time={avg_t:.3f}s  "
                      f"avg_div={statistics.mean(div_scores[-100:]):.3f}")
        except Exception as e:
            failures += 1
            elapsed = time.perf_counter() - t0
            gen_times.append(elapsed)
            div_scores.append(0.0)
            attempts_per.append(200)
            print(f"  [{i:4d}/{n}] ERROR: {e}")

    # ── Global statistics ──────────────────────────────────────────────
    total = successes + failures
    rej_rate = gen.stats["duplicate_rejections"] / max(gen.stats["total_attempts"] + n, 1)

    print()
    print("=" * 65)
    print("  RESULTS")
    print("=" * 65)
    print(f"  Total exams requested:     {n}")
    print(f"  Successful (unique):       {successes}  ({successes/n*100:.1f}%)")
    print(f"  Fallback (non-unique):     {failures}  ({failures/n*100:.1f}%)")
    print()
    print(f"  Duplicate rejections:      {gen.stats['duplicate_rejections']}")
    print(f"  Validation failures:       {gen.stats['validation_failures']}")
    print(f"  Avg attempts per exam:     {statistics.mean(attempts_per):.2f}")
    print(f"  Max attempts (single):     {max(attempts_per)}")
    print()

    print("  GENERATION TIME")
    print(f"    Min:   {min(gen_times):.4f}s")
    print(f"    Mean:  {statistics.mean(gen_times):.4f}s")
    print(f"    Max:   {max(gen_times):.4f}s")
    print(f"    Total: {sum(gen_times):.2f}s")
    print()

    print("  DIVERSITY SCORE DISTRIBUTION")
    print(f"    Min:    {min(div_scores):.4f}")
    print(f"    Mean:   {statistics.mean(div_scores):.4f}")
    print(f"    Max:    {max(div_scores):.4f}")
    if len(div_scores) >= 2:
        print(f"    StdDev: {statistics.stdev(div_scores):.4f}")

    # Distribution buckets
    buckets = {"[0.0–0.2)": 0, "[0.2–0.4)": 0, "[0.4–0.6)": 0, "[0.6–0.8)": 0, "[0.8–1.0]": 0}
    for s in div_scores:
        if s < 0.2:    buckets["[0.0–0.2)"] += 1
        elif s < 0.4:  buckets["[0.2–0.4)"] += 1
        elif s < 0.6:  buckets["[0.4–0.6)"] += 1
        elif s < 0.8:  buckets["[0.6–0.8)"] += 1
        else:          buckets["[0.8–1.0]"] += 1
    print()
    print("    Distribution:")
    for label, cnt in buckets.items():
        bar = "#" * (cnt * 30 // n)
        print(f"      {label}: {cnt:5d}  {bar}")
    print()

    print("  TEMPLATE COVERAGE (top 20 most used templates)")
    top20 = sorted(template_usage.items(), key=lambda x: x[1], reverse=True)[:20]
    for tid, cnt in top20:
        print(f"    {tid:<52}  {cnt:5d}x")
    print()

    # ── Bottleneck analysis ────────────────────────────────────────────
    rej_pct = failures / n * 100
    if rej_pct > 10:
        print("  ⚠  BOTTLENECK DETECTED — rejection rate exceeds 10%")
        print()
        print("  CAUSE: The structural duplicate pool is saturated.")
        print(f"  With {len(registry_size(gen))} templates and Level-3 position-matching,")
        print("  each slot can only produce a limited number of structurally unique")
        print("  exercises before hitting duplicates in the history.")
        print()
        print("  RECOMMENDED ACTIONS:")
        print("    1. Add 2–3 more template variants per slot — this expands the")
        print("       combinatorial space from 5^10=~10M to 7^10=~282M structural combos.")
        print("    2. Raise duplicate_threshold from 0.6 to 0.7 for large batches.")
        print("    3. Relax Level 3 to only check the first 8 positions (allow some reuse).")
        print("    4. Introduce parameter diversification: ensure param_signature changes")
        print("       on retry by using Latin hypercube sampling for parameter generation.")
    else:
        print(f"  OK — rejection rate {rej_pct:.1f}% is within the 10% target.")

    print()
    print("=" * 65)
    print("  Stress test complete.")
    print("=" * 65)
    return {
        "successes": successes,
        "failures": failures,
        "gen_times": gen_times,
        "attempts_per": attempts_per,
        "div_scores": div_scores,
        "template_usage": template_usage,
        "stats": gen.stats,
    }

def registry_size(gen):
    from bac_generator.generators.registry import registry as reg
    all_funcs = []
    for slot in range(1, 11):
        all_funcs.extend(reg.get_generators(slot))
    return all_funcs

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    run_stress_test(n, threshold)
