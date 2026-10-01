# Chat With Your Data

An AI-powered chatbot that answers plain-English questions about **any CSV or Excel file you upload** by automatically writing and running SQL queries.

Upload a dataset, ask something like *"which product has the highest rating?"*, and it translates your question into SQL, runs it against your data with DuckDB, and returns a real answer — no SQL knowledge required.

##  Live  
data-analytics-chatbot-fnsczxe3be8dvhwcpa4skq.streamlit.app

## How it works

```
Upload a file  →  Your question  →  Gemini (writes SQL)  →  DuckDB (runs SQL)  →  Answer + table
```

1. You upload a CSV or Excel file through the sidebar.
2. It's loaded into an in-memory [DuckDB](https://duckdb.org/) database.
3. When you ask a question, the app sends your question along with the table's schema to Google's Gemini API.
4. Gemini responds with a SQL query tailored to your question.
5. That query runs against your data, and the result is displayed in the chat as a table.
6. You can expand "View generated SQL" on any answer to see exactly what query was run.

## Tech stack

- **[Streamlit](https://streamlit.io/)** — chat interface and file upload
- **[DuckDB](https://duckdb.org/)** — fast, in-process SQL engine for querying the uploaded data directly
- **[Google Gemini API](https://ai.google.dev/)** (`gemini-3.6-flash`) — turns natural language into SQL
- **pandas** — data loading (CSV and Excel)

## Running it locally

1. Clone this repo and install dependencies:
   ```bash
   pip install pandas duckdb streamlit google-genai python-dotenv openpyxl
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
5. Upload any CSV or Excel file and start asking questions.

## Features

- **Upload your own dataset** — CSV or Excel, no fixed schema required
- Natural language → SQL query generation
- Live, in-memory SQL execution against the uploaded dataset
- Sidebar with dataset preview, column list, and one-click sample questions
- Friendly, human-readable error messages instead of raw API errors
- Clean, custom-designed dark UI
- Sample datasets included (`sample_sales_data.csv`, `apple_products.csv`) for quick testing

## What I'd improve next

- Validate generated SQL is read-only before executing it, for safety
- Auto-generate charts when a question implies a visual (trends, comparisons)
- Add conversation memory so follow-up questions can build on previous answers
- Automatic retry if the AI's generated SQL fails on the first try
- Deploy a live demo link

## Screenshots

*(Add a screenshot or short GIF of the chatbot here — this is the single most important thing for anyone browsing your repo.)*
