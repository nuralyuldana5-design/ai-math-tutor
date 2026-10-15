import json
import os
import re
import streamlit as st
from google import genai

st.set_page_config(page_title='AI Math Tutor', page_icon='📘')
st.title('📘 AI Math Tutor')
st.write('Grade 7 • Linear Equations with One Variable')

level = st.selectbox('Choose your difficulty level', ['Foundation', 'Standard', 'Advanced'])

if 'problem' not in st.session_state:
    st.session_state.problem = None
if 'current_level' not in st.session_state:
    st.session_state.current_level = None

api_key = st.secrets.get('GEMINI_API_KEY', os.getenv('GEMINI_API_KEY', ''))

if st.button('Generate new problem', type='primary'):
    if not api_key:
        st.error('Add GEMINI_API_KEY in Streamlit Secrets before generating problems.')
    else:
        prompt = f'''You are a careful Grade 7 mathematics teacher. Create ONE linear equation in one variable for difficulty {level}.
Foundation: x+a=b or ax=b, small integer solution, simple step-by-step hint.
Standard: ax+b=c, integer solution, moderate difficulty.
Advanced: brackets and variables on both sides, multi-step reasoning, integer solution.
Return ONLY a valid JSON object with string keys: problem, hint, solution, answer.
The problem must have exactly one integer solution. The answer is only the integer (e.g. "7").
Show correct algebraic steps in solution. Do not use markdown fences.'''
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model='gemini-3.8-flash', contents=prompt)
            raw = response.text.strip()
            raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw)
            data = json.loads(raw)
            if not all(isinstance(data.get(k), str) for k in ('problem','hint','solution','answer')):
                raise ValueError('Incomplete AI response')
            int(data['answer'])
            st.session_state.problem = data
            st.session_state.current_level = level
        except Exception as exc:
            st.error(f'Could not generate a problem: {exc}')

if st.session_state.problem and st.session_state.current_level == level:
    task = st.session_state.problem
    st.subheader('Solve the equation')
    st.latex(task['problem'].replace('=', ' = '))
    user_answer = st.text_input('Your answer: x =', key=f'answer_{level}_{task["problem"]}')
    if st.button('Check answer'):
        try:
            if int(user_answer.strip()) == int(task['answer']):
                st.success('Correct! 🎉')
            else:
                st.warning('Not quite. Try the hint!')
        except ValueError:
            st.warning('Enter an integer answer.')
    with st.expander('💡 Hint'):
        st.write(task['hint'])
    with st.expander('📖 Show solution'):
        st.write(task['solution'])
else:
    st.info('Select a level and click Generate new problem.')

st.caption('AI-generated mathematics should be reviewed for accuracy.')
