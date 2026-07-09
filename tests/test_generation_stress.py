import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bac_generator.generator import BACExamGenerator
from bac_generator.pdf.pdf_generator import build_pdf

def test_stress():
    generator = BACExamGenerator()
    lessons = [
        "Radicali", "Puteri", "Progresii", "Probabilități",
        "Funcții", "Logaritmi", "Numere complexe", "Trigonometrie",
        "Matrici", "Legi de compoziție", "Limite", "Derivate",
        "Integrale definite", "Polinoame"
    ]
    
    os.makedirs("test_outputs", exist_ok=True)
    
    specializations = ["M1", "M2", "M3", "M4"]
    
    print("Starting stress test: generating 50 BAC exams...")
    for i in range(50):
        # Generate the exam
        exam_data = generator.generate_exam(lessons)
        spec = specializations[i % len(specializations)]
        
        # Build Subject PDF
        sub_filepath = f"test_outputs/exam_{i+1}_subject.pdf"
        build_pdf(sub_filepath, exam_data, include_solutions=False, bac=spec)
        
        # Build Solutions PDF
        sol_filepath = f"test_outputs/exam_{i+1}_sol.pdf"
        build_pdf(sol_filepath, exam_data, include_solutions=True, bac=spec)
        
        # Assert file exists and has size > 0
        assert os.path.exists(sub_filepath) and os.path.getsize(sub_filepath) > 0
        assert os.path.exists(sol_filepath) and os.path.getsize(sol_filepath) > 0
        
        print(f"[{i+1}/50] Successfully generated and built PDFs for specialization {spec}.")
        
    print("\nSUCCESS: Stress test passed! 50 exams generated and compiled to PDF without any errors.")

if __name__ == "__main__":
    test_stress()
