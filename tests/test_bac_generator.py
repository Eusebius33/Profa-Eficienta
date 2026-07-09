import os
import unittest
import tempfile
import json
import sqlite3
from app import app
from bac_generator.generators import (
    gen_s1_ex1, gen_s1_ex2, gen_s1_ex3, gen_s1_ex4, gen_s1_ex5, gen_s1_ex6,
    gen_s2_ex1, gen_s2_ex2,
    gen_s3_ex1, gen_s3_ex2
)
from bac_generator.generators.registry import registry
from bac_generator.validators.verify import verify_exercise
from bac_generator.duplicate.similarity import DuplicateDetector, normalize_text, get_exact_hash, get_normalized_hash, get_template_param_hash
from bac_generator.generator import BACExamGenerator
from bac_generator.pdf.pdf_generator import build_pdf, clean_latex_for_pdf, strip_diacritics
import bac_generator.routes

class TestBACGenerator(unittest.TestCase):
    
    def setUp(self):
        # Configure app for testing
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SESSION_TYPE"] = "null"
        self.client = app.test_client()
        
    def test_generators(self):
        """Verify that all 10 slot wrappers produce valid exercise structures."""
        generators = [
            gen_s1_ex1, gen_s1_ex2, gen_s1_ex3, gen_s1_ex4, gen_s1_ex5, gen_s1_ex6,
            gen_s2_ex1, gen_s2_ex2,
            gen_s3_ex1, gen_s3_ex2
        ]
        
        for i, gen_func in enumerate(generators, 1):
            ex = gen_func()
            self.assertIn("id", ex, f"Generator {i} missing id")
            self.assertIn("text", ex, f"Generator {i} missing text")
            self.assertIn("solution", ex, f"Generator {i} missing solution")
            self.assertIn("points", ex, f"Generator {i} missing points")
            self.assertIn("params", ex, f"Generator {i} missing params")
            self.assertIn("lesson", ex, f"Generator {i} missing lesson")
            self.assertTrue(len(ex["text"]) > 0, f"Generator {i} produced empty text")
            self.assertTrue(len(ex["solution"]) > 0, f"Generator {i} produced empty solution")

    def test_all_variants_registration(self):
        """Verify that all expected variants are registered in the registry."""
        for slot in range(1, 11):
            funcs = registry.get_generators(slot)
            self.assertTrue(len(funcs) >= 3, f"Slot {slot} has fewer than 3 registered variants")

    def test_validation_module(self):
        """Verify that verify_exercise correctly flags mathematically invalid cases."""
        valid_ex = {
            "id": "test_valid",
            "text": "Calculați $2 + 2$.",
            "solution": "4",
            "params": {"a": 2, "b": 2}
        }
        self.assertTrue(verify_exercise(valid_ex))
        
        div_zero_ex = {
            "id": "test_div_zero",
            "text": "Calculați $\\frac{5}{0}$.",
            "solution": "inf",
            "params": {}
        }
        self.assertFalse(verify_exercise(div_zero_ex))
        
        invalid_log_base = {
            "id": "test_log_base",
            "text": "Calculați logaritmul.",
            "solution": "ok",
            "params": {"log_base": 1}
        }
        self.assertFalse(verify_exercise(invalid_log_base))

    def test_duplicate_detection(self):
        """
        Verify 4-level duplicate detection:
          L1 – exact text hash
          L2 – same (template_id, param_signature)
          L3 – same template_id at same position
          L4 – structural overlap >= threshold
        """
        detector = DuplicateDetector()

        # Text normalization: numbers replaced with [NUM]
        t1 = "Progresia aritmetica cu a1 = 2 si d = 3."
        t2 = "Progresia aritmetica cu a1 = 5 si d = 4."
        self.assertEqual(normalize_text(t1), normalize_text(t2))

        # Build a mock exam with template_id and param_signature fields
        template_ids = [
            "s1_arith_seq_nth_term", "s1_parabola_vertex", "s1_radical_equation",
            "s1_classical_probability", "s1_midpoint_segment", "s1_law_of_cosines",
            "s2_matrix_parametric_power", "s2_law_absorbing_element",
            "s3_derivative_log_product", "s3_integral_polynomial_volume",
        ]
        mock_exam_1 = [
            {"id": f"ex_{i}", "template_id": template_ids[i],
             "param_signature": f"k={i};v={i}",
             "text": f"Exercise text slot {i} value {i}"}
            for i in range(10)
        ]
        detector.register_exam(mock_exam_1)

        # Level 1: exact text match
        self.assertTrue(detector.check_level_1(mock_exam_1),
                        "L1 should detect exact text duplicate")

        # Level 2: same (template_id, param_signature) but different text
        mock_exam_2_same_tp = [
            {"id": f"ex_{i}", "template_id": template_ids[i],
             "param_signature": f"k={i};v={i}",
             "text": f"Completely different text slot {i}"}
            for i in range(10)
        ]
        self.assertTrue(detector.check_level_2(mock_exam_2_same_tp),
                        "L2 should detect same template+params at any position")

        # Level 2 should pass for genuinely new params
        mock_exam_2_new = [
            {"id": f"ex_{i}", "template_id": template_ids[i],
             "param_signature": f"k={i+999};v={i+999}",
             "text": f"Fresh text slot {i}"}
            for i in range(10)
        ]
        self.assertFalse(detector.check_level_2(mock_exam_2_new),
                         "L2 should pass for new param_signatures")

        # Level 3: same (template_id, param_signature) at same position
        mock_exam_3 = [
            {"id": f"ex_{i}", "template_id": template_ids[i],
             "param_signature": f"k={i};v={i}",   # SAME as mock_exam_1
             "text": f"Different numbers slot {i}"}
            for i in range(10)
        ]
        self.assertTrue(detector.check_level_3(mock_exam_3),
                        "L3 should detect same template+params at same position")

        # Level 4: structural overlap via set Jaccard — use isolated detector
        # Create a fresh detector without official exams to test in isolation
        class _IsolatedDetector(DuplicateDetector):
            def __init__(self):
                self.exact_hashes: set = set()
                self.template_param_hashes: set = set()
                self.past_exams: list = []

        iso = _IsolatedDetector()
        ref_tids = [f"ref_template_{i}" for i in range(10)]
        ref_exam_iso = [
            {"id": f"r{i}", "template_id": ref_tids[i],
             "param_signature": f"p={i}", "text": f"Ref text {i}"}
            for i in range(10)
        ]
        iso.register_exam(ref_exam_iso)

        # Level 4: structural overlap via set Jaccard — 9/10 same templates
        # Jaccard(9 shared, 1 different vs 10 ref) = 9/(9+1+1) = 9/11 ≈ 0.82 >= 0.6
        # But simpler: if candidate uses 9 of same + 1 new:
        #   union = 10 ref + 1 new = 11, intersection = 9, Jaccard = 9/11 ≈ 0.82
        shared9 = ref_tids[:9]
        exam_high_overlap = [
            {"id": f"ex_{j}", "template_id": tid,
             "param_signature": f"x={j}", "text": f"Overlap text {j}"}
            for j, tid in enumerate(shared9 + ["unique_new_template"])
        ]
        self.assertTrue(iso.check_level_4(exam_high_overlap, threshold=0.6),
                        "L4 should reject exam with ~82% structural overlap")

        # Fully novel exam (all new template_ids)
        novel_exam = [
            {"id": f"novel_{i}", "template_id": f"brand_new_template_{i}",
             "param_signature": f"p={i}", "text": f"Novel text {i}"}
            for i in range(10)
        ]
        self.assertFalse(detector.is_duplicate(novel_exam, threshold=0.6),
                         "is_duplicate should return False for fully novel exam")

        # Diversity score: novel exam should score close to 1.0
        score = detector.compute_diversity_score(novel_exam)
        self.assertGreater(score, 0.5, "Novel exam should have high diversity score")

    def test_latex_to_pdf_cleaning(self):
        """Verify diacritics and math formatting cleanups for PDFs."""
        latex_str = "Se consideră $f(x) = \\frac{x-1}{x+2}$ și $\\mathbb{R}$."
        cleaned = clean_latex_for_pdf(latex_str)
        self.assertNotIn("\\frac", cleaned)
        self.assertNotIn("$", cleaned)
        self.assertIn("R", cleaned)
        self.assertEqual(strip_diacritics("ăâîșț"), "aaist")

    def test_exam_generation_pipeline(self):
        """Verify end-to-end exam generation works successfully."""
        gen = BACExamGenerator()
        exam = gen.generate_exam()
        
        self.assertIn("exercises", exam)
        self.assertIn("html_preview", exam)
        self.assertIn("solution_preview", exam)
        self.assertEqual(len(exam["exercises"]), 10)
        
        # Check generation with lesson filtering
        filtered_exam = gen.generate_exam(selected_lessons=["Limite", "Derivate"])
        self.assertEqual(len(filtered_exam["exercises"]), 10)

    def test_pdf_generation(self):
        """Verify PDF compiler output on disk."""
        gen = BACExamGenerator()
        exam_data = gen.generate_exam()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "test_exam.pdf")
            build_pdf(pdf_path, exam_data, include_solutions=False)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertTrue(os.path.getsize(pdf_path) > 0)

    def test_deterministic_seeding(self):
        """Verify seed reproducibility (deterministic outputs)."""
        gen1 = BACExamGenerator()
        exam_1 = gen1.generate_exam(seed=42)
        gen2 = BACExamGenerator()
        exam_2 = gen2.generate_exam(seed=42)
        
        # Compare raw exercise text to ensure they are identical
        for i in range(10):
            self.assertEqual(exam_1["exercises"][i]["text"], exam_2["exercises"][i]["text"])
            self.assertEqual(exam_1["exercises"][i]["solution"], exam_2["exercises"][i]["solution"])
            
        # Ensure a different seed produces different results
        gen3 = BACExamGenerator()
        exam_3 = gen3.generate_exam(seed=43)
        differ = False
        for i in range(10):
            if exam_1["exercises"][i]["text"] != exam_3["exercises"][i]["text"]:
                differ = True
                break
        self.assertTrue(differ)

    def test_metadata_persistence(self):
        """Verify exam metadata structure and persistence on disk."""
        history_path = "bac_generator/metadata_history.json"
        
        # Reset file if it exists
        if os.path.exists(history_path):
            try:
                os.remove(history_path)
            except Exception:
                pass
                
        gen = BACExamGenerator()
        exam = gen.generate_exam(seed=100)
        
        self.assertIn("metadata", exam)
        meta = exam["metadata"]
        self.assertEqual(meta["seed"], 100)
        self.assertEqual(meta["generator_version"], "3.0.0")
        self.assertIn("exercise_fingerprints", meta)
        self.assertIn("diversity_score", meta,
                      "Metadata must include diversity_score")

        # Verify each fingerprint has template_id and param_signature
        for fp in meta["exercise_fingerprints"]:
            self.assertIn("template_id", fp, "Fingerprint must have template_id")
            self.assertIn("param_signature", fp, "Fingerprint must have param_signature")
            self.assertIn("topic", fp, "Fingerprint must have topic")
            self.assertIn("difficulty", fp, "Fingerprint must have difficulty")

        # Check that it got written to history file
        self.assertTrue(os.path.exists(history_path))
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
            self.assertTrue(len(history) >= 1)
            self.assertEqual(history[-1]["seed"], 100)

    def test_routes_integration(self):
        """Verify routes blueprint using the Flask test client and an in-memory SQLite DB."""
        # 1. Mock DB connection to run in-memory for testing
        real_conn = sqlite3.connect(":memory:")
        real_conn.row_factory = sqlite3.Row
        
        class MockConnection:
            def __init__(self, conn):
                self.conn = conn
            def cursor(self):
                return self.conn.cursor()
            def commit(self):
                return self.conn.commit()
            def close(self):
                pass
            def execute(self, *args, **kwargs):
                return self.conn.execute(*args, **kwargs)
            def __getattr__(self, name):
                return getattr(self.conn, name)
                
        mock_conn = MockConnection(real_conn)
        
        cursor = real_conn.cursor()
        cursor.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            exam_data TEXT
        )
        """)
        
        bac_generator.routes.get_db_connection = lambda: mock_conn
        
        # 2. Test generation POST route
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1 # Bypass login check
            
        response = self.client.post("/generate-bac/123", data={
            "lessons": ["Limite", "Derivate"],
            "prompt": "Test Prompt"
        })
        self.assertEqual(response.status_code, 302) # Should redirect back to mode page
        
        # Check database records
        cursor.execute("SELECT * FROM messages WHERE role = 'assistant'")
        assistant_msg = cursor.fetchone()
        self.assertIsNotNone(assistant_msg)
        self.assertEqual(assistant_msg["conversation_id"], 123)
        self.assertIn("exercises", assistant_msg["exam_data"])
        
        # 3. Test PDF download route
        assistant_id = assistant_msg["id"]
        response = self.client.get(f"/generate-bac/download/{assistant_id}?type=subject")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        
        real_conn.close()

if __name__ == "__main__":
    unittest.main()
