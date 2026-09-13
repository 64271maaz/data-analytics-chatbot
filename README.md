# Chat With Your Data

An AI-powered chatbot that answers plain-English questions about a dataset by automatically writing and running SQL queries.

Ask something like *"which product has the highest star rating?"* and it translates your question into SQL, runs it against the data with DuckDB, and returns a real answer — no SQL knowledge required.

## How it works

```
Your question  →  Gemini (writes SQL)  →  DuckDB (runs SQL)  →  Answer + table
```

1. A CSV file is loaded into an in-memory [DuckDB](https://duckdb.org/) database.
2. When you ask a question, the app sends your question along with the table's schema to Google's Gemini API.
3. Gemini responds with a SQL query tailored to your question.
4. That query runs against the data, and the result is displayed in the chat as a table.
5. You can expand "View generated SQL" on any answer to see exactly what query was run.

## Tech stack

- **[Streamlit](https://streamlit.io/)** — chat interface
- **[DuckDB](https://duckdb.org/)** — fast, in-process SQL engine for querying the CSV directly
- **[Google Gemini API](https://ai.google.dev/)** (`gemini-3.6-flash`) — turns natural language into SQL
- **pandas** — data loading

## Running it locally

1. Clone this repo and install dependencies:
   ```bash
   pip install pandas duckdb streamlit google-genai python-dotenv
   ```
2. Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
3. Create a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your-key-here
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Features

- Natural language → SQL query generation
- Live, in-memory SQL execution against the uploaded dataset
- Sidebar with dataset preview, column list, and one-click sample questions
- Friendly, human-readable error messages instead of raw API errors
- Clean, custom-designed dark UI

## What I'd improve next

- Let users upload their own CSV/Excel file instead of using a fixed dataset
- Validate generated SQL is read-only before executing it, for safety
- Auto-generate charts when a question implies a visual (trends, comparisons)
- Add conversation memory so follow-up questions can build on previous answers
- Deploy a live demo link

## Screenshots

*(Add a screenshot or short GIF of the chatbot here once you have one — this is the single most important thing for anyone browsing your repo.)*
