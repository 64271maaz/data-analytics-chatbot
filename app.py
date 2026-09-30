import os
import time
import random

import streamlit as st
import pandas as pd
import duckdb

from google import genai
from dotenv import load_dotenv


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv(override=True)

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error(
        "GEMINI_API_KEY not found. "
        "Please add it to your .env file."
    )
    st.stop()


client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.8-flash"


st.set_page_config(
    page_title="Data Analytics Chatbot",
    page_icon="◆",
    layout="wide"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

.stApp {
    background: #0d1117;
}

/* Top accent line */
.stApp::before {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #d4a94c, #8a6d2f);
    z-index: 999;
}


/* Hero */
.hero {
    padding: 2rem 0 1.5rem 0;
    border-bottom: 1px solid #1f242e;
    margin-bottom: 1.5rem;
}

.hero .eyebrow {
    color: #d4a94c;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin-bottom: 0.4rem;
}

.hero h1 {
    font-size: 2.4rem;
    font-weight: 800;
    color: #f0f2f5;
    margin: 0 0 0.3rem 0;
}

.hero p {
    color: #7d8590;
    font-size: 1.02rem;
    margin: 0;
}


/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0a0c10;
    border-right: 1px solid #1f242e;
}

section[data-testid="stSidebar"] h2 {
    font-size: 0.95rem;
    font-weight: 700;
    color: #e6e8eb;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
    color: #9198a1;
}


/* Sidebar buttons */
section[data-testid="stSidebar"] button {
    background: #12151c !important;
    border: 1px solid #232833 !important;
    border-radius: 8px !important;
    color: #c9d1d9 !important;
}

section[data-testid="stSidebar"] button:hover {
    background: #171b24 !important;
    border-color: #d4a94c !important;
}


/* Chat messages */
div[data-testid="stChatMessage"] {
    background: #12151c;
    border: 1px solid #1f242e;
    border-radius: 10px;
    padding: 0.6rem;
    margin-bottom: 0.6rem;
}


/* Dataframes */
div[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #1f242e;
}


/* Alerts */
div[data-testid="stAlert"] {
    border-radius: 8px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "df" not in st.session_state:
    st.session_state.df = None

if "con" not in st.session_state:
    st.session_state.con = None

if "filename" not in st.session_state:
    st.session_state.filename = None


# =========================================================
# GEMINI REQUEST WITH RETRY
# =========================================================

def gemini_request(prompt, max_retries=4):

    """
    Sends request to Gemini.

    Automatically retries temporary:
    - 503 Service Unavailable
    - 429 Rate Limit
    - 500 Server errors
    """

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            return response

        except Exception as e:

            error_text = str(e)

            temporary_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "500" in error_text
                or "INTERNAL" in error_text
            )

            if not temporary_error:

                raise e

            # Last attempt
            if attempt == max_retries - 1:

                raise e

            # Exponential backoff
            delay = (2 ** attempt) + random.uniform(0, 1)

            time.sleep(delay)


# =========================================================
# LOAD DATASET
# =========================================================

def load_uploaded_file(uploaded_file):

    file_name = uploaded_file.name.lower()

    try:

        if file_name.endswith(".csv"):

            df = pd.read_csv(uploaded_file)

        elif (
            file_name.endswith(".xlsx")
            or file_name.endswith(".xls")
        ):

            df = pd.read_excel(uploaded_file)

        else:

            st.error(
                "Unsupported file type. "
                "Please upload CSV or Excel file."
            )

            return None, None


        # Remove empty rows
        df = df.dropna(how="all")

        # Remove empty columns
        df = df.dropna(axis=1, how="all")


        # Clean column names
        df.columns = [
            str(col).strip()
            for col in df.columns
        ]


        # Create DuckDB connection
        con = duckdb.connect(
            database=":memory:"
        )


        # Register dataframe
        con.register(
            "data_table",
            df
        )


        return df, con


    except Exception as e:

        st.error(
            f"Could not read the file: {e}"
        )

        return None, None


# =========================================================
# CREATE DATASET DESCRIPTION
# =========================================================

def create_schema_description(df):

    columns_info = []

    for column in df.columns:

        columns_info.append(
            f"- {column} "
            f"(type: {df[column].dtype})"
        )


    sample_data = df.head(5).to_string(
        index=False
    )


    schema = f"""
Table name: data_table

Columns:
{chr(10).join(columns_info)}

Sample rows:
{sample_data}
"""


    return schema


# =========================================================
# GENERATE SQL
# =========================================================

def generate_sql(question, df):

    schema_description = (
        create_schema_description(df)
    )


    prompt = f"""
You are an expert DuckDB SQL developer.

The user has uploaded a dataset.

{schema_description}

The DuckDB table name is:

data_table

User question:

"{question}"

Instructions:

1. Understand the user's question.
2. Generate ONE valid DuckDB SQL query.
3. Use only columns that actually exist.
4. Use table name data_table.
5. Do not invent columns.
6. Do not modify data.
7. Do not delete data.
8. Only generate SELECT queries.
9. Return ONLY SQL.
10. Do not use markdown.
11. Do not use ```.

SQL:
"""


    response = gemini_request(
        prompt
    )


    sql = response.text.strip()


    # Remove markdown if Gemini adds it
    sql = sql.replace(
        "```sql",
        ""
    )

    sql = sql.replace(
        "```SQL",
        ""
    )

    sql = sql.replace(
        "```",
        ""
    )


    sql = sql.strip()


    return sql


# =========================================================
# VALIDATE SQL
# =========================================================

def validate_sql(sql):

    sql_upper = sql.upper().strip()


    # Only SELECT allowed
    if not sql_upper.startswith("SELECT"):

        raise Exception(
            "Only SELECT queries are allowed."
        )


    # Block dangerous SQL keywords
    dangerous_keywords = [
        "DROP ",
        "DELETE ",
        "UPDATE ",
        "INSERT ",
        "ALTER ",
        "CREATE ",
        "TRUNCATE ",
        "ATTACH ",
        "COPY ",
        "INSTALL ",
        "LOAD "
    ]


    for keyword in dangerous_keywords:

        if keyword in sql_upper:

            raise Exception(
                "Unsafe SQL query detected."
            )


# =========================================================
# CREATE SIMPLE HUMAN ANSWER
# =========================================================

def create_human_answer(
    question,
    result
):

    # No results
    if result.empty:

        return (
            "I couldn't find any matching "
            "data in your dataset."
        )


    # One cell result
    if (
        len(result) == 1
        and len(result.columns) == 1
    ):

        value = result.iloc[0, 0]

        return (
            f"The answer is **{value}**."
        )


    # One row result
    if len(result) == 1:

        row = result.iloc[0]

        parts = []

        for column in result.columns:

            value = row[column]

            parts.append(
                f"**{column}:** {value}"
            )


        return (
            "Here is the result:\n\n"
            + "\n\n".join(parts)
        )


    # Multiple rows
    row_count = len(result)

    return (
        f"I found **{row_count} records** "
        f"matching your question. "
        f"The detailed results are shown below."
    )


# =========================================================
# FRIENDLY ERROR
# =========================================================

def friendly_error(e):

    msg = str(e)


    if (
        "429" in msg
        or "RESOURCE_EXHAUSTED" in msg
        or "quota" in msg.lower()
    ):

        return (
            "⚠️ Gemini API usage limit reached. "
            "Please wait a little and try again."
        )


    if (
        "invalid_api_key" in msg
        or "authentication" in msg.lower()
        or "API_KEY_INVALID" in msg
    ):

        return (
            "⚠️ Gemini API key problem. "
            "Please check your .env file."
        )


    if (
        "503" in msg
        or "UNAVAILABLE" in msg
    ):

        return (
            "⚠️ Gemini is temporarily unavailable. "
            "The app already tried automatically. "
            "Please try again after a short wait."
        )


    if "404" in msg:

        return (
            "⚠️ Gemini model was not found. "
            "Please check the model name and "
            "Google GenAI SDK version."
        )


    return (
        "⚠️ I couldn't answer this question.\n\n"
        f"Details: {msg}"
    )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("📂 Upload Dataset")


    uploaded_file = st.file_uploader(
        "Upload your CSV or Excel file",
        type=[
            "csv",
            "xlsx",
            "xls"
        ]
    )


    # -----------------------------------------------------
    # Upload file
    # -----------------------------------------------------

    if uploaded_file is not None:

        if (
            st.session_state.filename
            != uploaded_file.name
        ):

            df, con = load_uploaded_file(
                uploaded_file
            )


            if df is not None:

                st.session_state.df = df

                st.session_state.con = con

                st.session_state.filename = (
                    uploaded_file.name
                )

                # New dataset = new chat
                st.session_state.messages = []

                st.success(
                    "Dataset uploaded successfully!"
                )


    # -----------------------------------------------------
    # Dataset information
    # -----------------------------------------------------

    if st.session_state.df is not None:

        df = st.session_state.df


        st.divider()

        st.header("Dataset")


        st.write(
            f"**File:** "
            f"{st.session_state.filename}"
        )


        st.write(
            f"**Rows:** {len(df)}"
        )


        st.write(
            f"**Columns:** {len(df.columns)}"
        )


        # Preview
        st.dataframe(
            df.head(5),
            height=180
        )


        # -------------------------------------------------
        # Columns
        # -------------------------------------------------

        with st.expander(
            "📋 Columns"
        ):

            for column in df.columns:

                st.write(
                    f"• `{column}`"
                )


        # -------------------------------------------------
        # Sample questions
        # -------------------------------------------------

        st.divider()

        st.header("💡 Try asking")


        sample_questions = [

            "What are the top 5 products?",

            "What is the average price?",

            "Which product has the highest rating?",

            "Show the 5 cheapest products."

        ]


        clicked_question = None


        for q in sample_questions:

            if st.button(
                q,
                use_container_width=True
            ):

                clicked_question = q


    else:

        st.info(
            "👆 Upload a CSV or Excel dataset "
            "to start."
        )

        clicked_question = None


# =========================================================
# MAIN HERO
# =========================================================

st.markdown("""
<div class="hero">

    <div class="eyebrow">
        AI DATA ANALYTICS
    </div>

    <h1>
        Chat With Your Data
    </h1>

    <p>
        Upload your dataset and ask questions
        in plain English.
    </p>

</div>
""", unsafe_allow_html=True)


# =========================================================
# NO DATASET
# =========================================================

if st.session_state.df is None:

    st.info(
        "📂 Please upload a CSV or Excel dataset "
        "from the left sidebar."
    )


    st.markdown("""
### How it works

**Step 1:** Upload your CSV or Excel dataset

**Step 2:** System reads your data

**Step 3:** Ask a question in normal English

**Step 4:** Gemini understands the question

**Step 5:** Gemini generates SQL

**Step 6:** DuckDB analyzes your dataset

**Step 7:** Chatbot gives you the answer
""")


    st.stop()


# =========================================================
# CHAT HISTORY
# =========================================================

for msg in st.session_state.messages:

    with st.chat_message(
        msg["role"]
    ):

        st.write(
            msg["content"]
        )


        if "table" in msg:

            st.dataframe(
                msg["table"],
                use_container_width=True
            )


        if "sql" in msg:

            with st.expander(
                "🔍 View Generated SQL"
            ):

                st.code(
                    msg["sql"],
                    language="sql"
                )


# =========================================================
# CHAT INPUT
# =========================================================

user_question = st.chat_input(
    "Ask a question about your dataset..."
)


question_to_run = (
    user_question
    or clicked_question
)


# =========================================================
# PROCESS QUESTION
# =========================================================

if question_to_run:

    # -----------------------------------------------------
    # USER MESSAGE
    # -----------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question_to_run
        }
    )


    with st.chat_message("user"):

        st.write(
            question_to_run
        )


    # -----------------------------------------------------
    # ASSISTANT
    # -----------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "🤖 Analyzing your data..."
        ):

            try:

                df = (
                    st.session_state.df
                )

                con = (
                    st.session_state.con
                )


                # =========================================
                # STEP 1: Gemini creates SQL
                # =========================================

                sql = generate_sql(
                    question_to_run,
                    df
                )


                # =========================================
                # STEP 2: Validate SQL
                # =========================================

                validate_sql(sql)


                # =========================================
                # STEP 3: Run SQL in DuckDB
                # =========================================

                result = con.execute(
                    sql
                ).fetchdf()


                # =========================================
                # STEP 4: Create answer locally
                # =========================================

                answer = create_human_answer(
                    question_to_run,
                    result
                )


                # =========================================
                # SHOW ANSWER
                # =========================================

                st.write(
                    answer
                )


                # =========================================
                # SHOW DATA
                # =========================================

                if not result.empty:

                    st.write(
                        "### 📊 Data Result"
                    )


                    st.dataframe(
                        result,
                        use_container_width=True
                    )


                else:

                    st.info(
                        "No matching data was found."
                    )


                # =========================================
                # SHOW SQL
                # =========================================

                with st.expander(
                    "🔍 View Generated SQL"
                ):

                    st.code(
                        sql,
                        language="sql"
                    )


                # =========================================
                # SAVE CHAT
                # =========================================

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sql": sql,
                        "table": result
                    }
                )


            except Exception as e:

                error_msg = friendly_error(e)


                st.warning(
                    error_msg
                )


                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_msg
                    }
                )