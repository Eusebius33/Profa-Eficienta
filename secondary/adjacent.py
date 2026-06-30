from google.genai import types
from secondary.ai import generate_content

# =========================================================
# MODE 2 - QUICK ACTIONS (nu respecta restrictiile din translate_math)
# =========================================================

def generate_exercises_free(n, style, school_class, bac):
    full_prompt = f"""
    Stil: {style}
    Clasa: {school_class}
    BAC: {bac}
    Numar de exercitii cerute: {n}
    """

    return generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=f"""
            Genereaza exact {n} exercitii de matematica noi, originale,
            adaptate stilului, clasei si tipului de BAC primite. 

            Reguli OBLIGATORII de formatare:
            NU FOLOSI CIFRE EXISTENTE DIN ULTIMUL EXERCITIU
            SCRIE STRICT EXERCITII FOARTE ASEMANATOARE CU CEL PRIMIT, 
            NU FOLOSI ALTE LECTII, STRICT EXERCITII DIN LECTIA EXERCITIULUI PRIMIT
            NU REPETA EXERCITIUL
            IN FUNCTIE DE CATE EXERCITII TI S AU CERUT MARESTE TREPTAT DIFICTULTATEA(EXEMPLU:n=5, ex1:usor. ex2:putin sub nivelul exercitiului primit. ex3:acelasi nivel de dificultate ex4: putim greu ex5:greu)
            Daca ai primit integrala, generezi alte integrale, definite sau nedefinite, cu rezolvare prin parti sau cu rezolvare prin formula sau prin schimbare de variabila
            EXEMPLU:∫x^2dx . Iar tu generezi alte integrale care se rezolva prin formule nedefinite. Daca primesti definita, faci definite
            - nu baga introduceri, doar scrie exercitiile
            - foloseste delimitatori $$ $$ pentru formulele LaTeX
            - nu folosi alte delimitatoare latex (fara \\(, \\[, etc.)
            - fiecare exercitiu trebuie sa fie pe randuri separate, clar delimitat
              de celelalte exercitii (linie goala intre ele)
            - NU lipi exercitiile unul de altul pe un singur rand
            - poti adauga un enunt scris normal, in limbaj natural, inainte de
              formulele LaTeX ale fiecarui exercitiu
            - numeroteaza exercitiile (1, 2, 3...)
            """,
            temperature=0.7
        )
    )


def solve_step_by_step(exercise_text, style, school_class, bac):
    full_prompt = f"""
    Stil: {style}
    Clasa: {school_class}
    BAC: {bac}

    Exercitiul de rezolvat:
    {exercise_text}
    """

    return generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction="""
            Esti un profesor de matematica. Rezolva exercitiul primit COMPLET,
            pas cu pas,ca un barem de rezolvare bac fiecare punct in parte. rezolvare matematica pt a verifica un profesor pasii
            Exemplu intx^2dx=(x^n+1)/(n+1)+C=(x^2+1)/(2+1)+C=x^3/3+C
            Reguli OBLIGATORII:
            - nu scrie nimic altceva in afara de rezolvarea exercitiului cum se rezolva la BAC
            - NU repeta doar enuntul / formula initiala ca "rezolvare"
            - arata fiecare pas de calcul, in ordine
            - explica in cateva cuvinte max(ce metoda folosesti), nu doar formule goale
            - foloseste delimitatori $$ $$ pentru formulele LaTeX
            - nu folosi alte delimitatoare latex
            - formateaza pe paragrafe separate, NU pe un singur rand
            - la final scrie rezultatul final clar evidentiat
            """,
            temperature=0.3
        )
    )