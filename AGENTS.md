# Repository Guidelines

## Project Structure & Module Organization
`app.py` is the Streamlit entry point that orchestrates UI, ingestion, and chat flows. Core modules in `src/` include `database_manager.py` for SQLite storage, `document_processor.py` for normalising files, `ingestion_manager.py` for dataset scans, and `chat_assistant.py` with shared AI utilities in `ai_client.py`. Place spreadsheets inside `dataset/documents/` and medical imagery inside `dataset/images/`. Copy `env_example.txt` to `.env` before running so keys resolve at startup.

## Build, Test, and Development Commands
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Append `-- --debug` when you need verbose logging. Run `python -m src.ingestion_manager` to dry-run ingestion; it reports pending files and ensures folders exist. Refresh sample assets under `dataset/` whenever you change schema expectations or add new modalities.

## Coding Style & Naming Conventions
Apply PEP 8 with 4-space indents, snake_case functions, and PascalCase classes. Keep UI code in `app.py` and route business logic into `src/` helpers. Document public methods with short docstrings, add type hints on new functions, and guard scripts with `if __name__ == "__main__":`. When editing inline CSS pushed through `st.markdown`, leave a brief comment describing the selector block.

## Testing Guidelines
There is no automated suite yet; add `pytest` cases under `tests/` named `test_*.py`. Mock OpenAI, Gemini, and Cloud Vision clients so tests stay offline-friendly, and point `DatabaseManager` to a temporary SQLite file per test. Before opening a PR, run a manual circuit: populate `dataset/documents/clinical_data.xlsx`, launch Streamlit, ingest data, and confirm chat answers for at least one patient scenario.

## Commit & Pull Request Guidelines
Use conventional commits (e.g., `feat: support gemini vision fallback`) and keep schema, UI, and platform changes in separate commits. PRs should summarise intent, list commands or tests executed, link issues, and attach screenshots or console excerpts for UX-facing updates. Call out configuration shifts to `.env` or dataset contracts explicitly so reviewers can replicate the setup.

## Security & Configuration Tips
Store secrets only in `.env` or per-session environment variables; never commit credentials, PHI, or `key.json`. Rotate API keys before demos and scrub logs of patient identifiers. When sharing example datasets, rely on anonymised or generated records and note any cleansing steps in the PR body.
