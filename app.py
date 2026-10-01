import os
import streamlit as st
import pandas as pd
import duckdb
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="Data Analytics Chatbot", page_icon="◆", layout="wide")

# --- Custom styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
    .stApp { background: #0d1117; }
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #d4a94c, #8a6d2f); z-index: 999;
    }
    @keyframes riseIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .hero { padding: 2rem 0 1.5rem 0; animation: riseIn 0.5s ease-out; border-bottom: 1px solid #1f242e; margin-bottom: 1.5rem; }
    .hero .eyebrow { color: #d4a94c; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.04em; margin-bottom: 0.4rem; }
    .hero h1 { font-size: 2.4rem; font-weight: 800; color: #f0f2f5; letter-spacing: -0.02em; margin: 0 0 0.3rem 0; line-height: 1.1; }
    .hero p { color: #7d8590; font-size: 1.02rem; margin: 0; }
    section[data-testid="stSidebar"] { background: #0a0c10; border-right: 1px solid #1f242e; }
    section[data-testid="stSidebar"] h2 { font-size: 0.95rem; font-weight: 700; color: #e6e8eb; letter-spacing: -0.01em; }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span { color: #9198a1; }
    section[data-testid="stSidebar"] button {
        background: #12151c !important; border: 1px solid #232833 !important; border-radius: 8px !important;
        color: #c9d1d9 !important; text-align: left !important; font-size: 0.85rem !important;
        transition: border-color 0.15s ease, background 0.15s ease;
    }
    section[data-testid="stSidebar"] button:hover { background: #171b24 !important; border-color: #d4a94c !important; color: #f0f2f5 !important; }
    div[data-testid="stChatMessage"] { background: #12151c; border: 1px solid #1f242e; border-radius: 10px; padding: 0.6rem; margin-bottom: 0.6rem; }
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; border: 1px solid #1f242e; }
    div[data-testid="stChatInput"] { border-radius: 10px; border-color: #232833 !important; }
    div[data-testid="stAlert"] { border-radius: 8px; }
    details { background: #0a0c10; border: 1px solid #1f242e; border-radius: 6px; }
    summary { color: #9198a1 !important; font-size: 0.85rem; }
    div[data-testid="stFileUploader"] { background: #12151c; border: 1px dashed #2d3348; border-radius: 10px; padding: 0.5rem; }
    .step-row { padding: 0.4rem 0; color: #c9d1d9; border-bottom: 1px solid #1a1e27; }
    .step-row b { color: #d4a94c; }
</style>
""", unsafe_allow_html=True)

def ask_question(question, schema_description):
    prompt = f"""You are a SQL expert. Given this table schema and sample data:

{schema_description}

Write a single DuckDB SQL query to answer this question: "{question}"

Only output the raw SQL query. No explanation, no markdown formatting, no backticks."""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    sql = response.text.strip()

    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()

    return sql

def friendly_error(e):
    msg = str(e)
    if "credit balance is too low" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return "⚠️ The AI service hit its usage limit right now. (Not a bug — try again in a moment.)"
    if "invalid_api_key" in msg or "authentication" in msg.lower() or "API_KEY_INVALID" in msg:
        return "⚠️ There's an issue with the API key setup. Double-check your .env file."
    if "UNAVAILABLE" in msg or "503" in msg:
        return "⚠️ The AI service is temporarily overloaded. Please try again in a few seconds."
    return f"⚠️ I couldn't answer that — the query may not match the data. Try rephrasing your question.\n\nDetails: {msg}"

# --- Sidebar: upload ---
with st.sidebar:
    st.header("Upload Dataset")
    uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx", "xls"])

    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        source_name = uploaded_file.name

        con = duckdb.connect(database=":memory:")
        con.register("sales", df)

        st.success(f"Loaded: {source_name}")
        st.write(f"{len(df)} rows · {len(df.columns)} columns")
        st.dataframe(df.head(5), height=180)

        with st.expander("Columns"):
            for col in df.columns:
                st.write(f"`{col}`")

        st.divider()
        st.header("Try asking")
        sample_questions = [
            "How many rows are in this dataset?",
            "Show me the first 5 rows",
            "What are the column names and their data types?",
        ]
        clicked_question = None
        for q in sample_questions:
            if st.button(q, use_container_width=True):
                clicked_question = q
    else:
        df = None
        con = None
        source_name = None
        clicked_question = None

# --- Main area ---
st.markdown("""
<div class="hero">
    <div class="eyebrow">DATA ANALYTICS CHATBOT</div>
    <h1>Chat With Your Data</h1>
    <p>Upload your dataset and ask questions in plain English.</p>
</div>
""", unsafe_allow_html=True)

if df is None:
    st.info("📁 Please upload a CSV or Excel dataset from the left sidebar to get started.")

    st.markdown("### How it works")
    steps = [
        ("1", "Upload your CSV or Excel dataset"),
        ("2", "The app reads your data"),
        ("3", "Ask a question in plain English"),
        ("4", "Gemini understands the question"),
        ("5", "Gemini generates a SQL query"),
        ("6", "DuckDB runs it against your dataset"),
        ("7", "The chatbot gives you the answer"),
    ]
    steps_html = "".join(
        f'<div class="step-row"><b>Step {n}:</b> {desc}</div>' for n, desc in steps
    )
    st.markdown(f'<div>{steps_html}</div>', unsafe_allow_html=True)

else:
    schema_description = f"""
Table name: sales
Columns: {', '.join(df.columns)}
Sample rows:
{df.head(3).to_string()}
"""

    if "current_source" not in st.session_state or st.session_state.current_source != source_name:
        st.session_state.messages = []
        st.session_state.current_source = source_name

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "sql" in msg:
                with st.expander("View generated SQL"):
                    st.code(msg["sql"], language="sql")
            if "table" in msg:
                st.dataframe(msg["table"], use_container_width=True)

    user_question = st.chat_input("Ask a question about your data...")
    question_to_run = user_question or clicked_question

    if question_to_run:
        st.session_state.messages.append({"role": "user", "content": question_to_run})
        with st.chat_message("user"):
            st.write(question_to_run)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    sql = ask_question(question_to_run, schema_description)
                    result = con.execute(sql).fetchdf()
                    st.write("Here's what I found:")
                    st.dataframe(result, use_container_width=True)
                    with st.expander("View generated SQL"):
                        st.code(sql, language="sql")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Here's what I found:",
                        "sql": sql,
                        "table": result
                    })
                except Exception as e:
                    error_msg = friendly_error(e)
                    st.warning(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
