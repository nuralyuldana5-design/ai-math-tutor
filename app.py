import json
import os
import re
import streamlit as st
import sympy as sp
from google import genai

st.set_page_config(page_title="AI Math Tutor", page_icon="📘")
st.title("📘 AI Math Tutor")
st.write("Grade 7 • Linear Equations with One Variable")

level = st.selectbox("Choose your difficulty level", ["Foundation", "Standard", "Advanced"])

if "problem" not in st.session_state:
    st.session_state.problem = None
if "current_level" not in st.session_state:
    st.session_state.current_level = None

api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
x = sp.Symbol("x")


def verify_equation(problem):
    """Safely parse a simple one-variable linear equation and solve it exactly."""
    cleaned = problem.replace("\\(", "").replace("\\)", "")
    cleaned = cleaned.replace("\\left", "").replace("\\right", "")
    cleaned = cleaned.replace("\\cdot", "*").replace("×", "*").replace("−", "-")
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = re.sub(r"\\(?:text|mathrm)\b", "", cleaned)
    cleaned = cleaned.replace(" ", "")
    cleaned = re.sub(r"(?i)^solve(?:for)?x:", "", cleaned)
    if cleaned.count("=") != 1:
        raise ValueError("Equation must contain exactly one equals sign")
    if not re.fullmatch(r"[0-9xX+*/().=\-]+", cleaned):
        raise ValueError("Unsupported equation format")
    left, right = cleaned.lower().split("=")
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
    transforms = standard_transformations + (implicit_multiplication_application,)
    # The strict character whitelist above prevents arbitrary names or Python source.
    lhs = parse_expr(left, local_dict={"x": x}, global_dict={"__builtins__": {}, "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational}, transformations=transforms, evaluate=True)
    rhs = parse_expr(right, local_dict={"x": x}, global_dict={"__builtins__": {}, "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational}, transformations=transforms, evaluate=True)
    expression = sp.expand(lhs - rhs)
    poly = sp.Poly(expression, x)
    if poly.degree() != 1:
        raise ValueError("The equation must be linear with one unique solution")
    result = sp.solve(expression, x)
    if len(result) != 1 or result[0].is_integer is not True:
        raise ValueError("The answer must be an integer")
    return int(result[0]), sp.latex(sp.Eq(lhs, rhs, evaluate=False))



if st.button("Generate new problem", type="primary"):
    st.session_state.problem = None
    st.session_state.current_level = None

    if not api_key:
        st.error("Add GEMINI_API_KEY in Streamlit Secrets.")
    else:
        previous_problems = st.session_state.get(
            "previous_problems", []
        )

        prompt = f'''You are a careful Grade 7 mathematics teacher.
Create ONE NEW linear equation for difficulty level: {level}.

Foundation: x+a=b or ax=b, small integer solution.
Standard: ax+b=c, moderate difficulty, integer solution.
Advanced: brackets and variables on both sides, multi-step reasoning.

IMPORTANT RULES:
1. Choose an integer solution FIRST.
2. Construct an equation with exactly one solution.
3. Do not repeat equations from this list: {previous_problems}.
4. Provide a hint and a correct step-by-step solution.
5. Keep the original equation unchanged.

Return ONLY valid JSON with string keys:
problem, hint, solution, answer.
The answer must be an integer written as a string.
Do not use markdown fences.'''

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
            raw = (response.text or "").strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
            data = json.loads(raw)
            if not all(isinstance(data.get(k), str) for k in ("problem", "hint", "solution", "answer")):
                raise ValueError("Incomplete AI response")
            actual_answer, equation_latex = verify_equation(data["problem"])
            if int(data["answer"].strip()) != actual_answer:
                raise ValueError("AI answer did not match the equation. Generate another problem.")
            data["verified_answer"] = actual_answer
            data["equation_latex"] = equation_latex
            st.session_state.problem = data
            if "previous_problems" not in st.session_state:
                st.session_state.previous_problems = []

            st.session_state.previous_problems.append(
                data["problem"]
            )
            st.session_state.current_level = level
        except Exception as exc:
            st.error(f"Could not generate a valid problem: {exc}")

if st.session_state.problem and st.session_state.current_level == level:
    task = st.session_state.problem
    st.subheader("Solve the equation")
    st.latex(task["equation_latex"])
    user_answer = st.text_input("Your answer: x =", key=f'answer_{level}_{task["problem"]}')
    if st.button("Check answer"):
        try:
            if sp.Rational(user_answer.strip()) == task["verified_answer"]:
                st.success("Correct! 🎉")
            else:
                st.warning("Not quite. Try the hint!")
        except (ValueError, TypeError, ZeroDivisionError):
            st.warning("Enter a number, such as 7 or 3/2.")
    with st.expander("💡 Hint"):
        st.write(task["hint"])
    with st.expander("📖 Show solution"):
        st.write(task["solution"])
        st.info(f'Verified answer: x = {task["verified_answer"]}')
else:
    st.info("Select a level and click Generate new problem.")

st.caption("SymPy verifies the equation and answer. AI-written explanations should still be reviewed for accuracy.")
