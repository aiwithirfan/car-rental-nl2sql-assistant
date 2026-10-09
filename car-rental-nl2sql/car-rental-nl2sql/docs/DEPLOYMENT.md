# Deployment guide

## 1. Push to GitHub
1. Create an empty repository on github.com (e.g. `car-rental-nl2sql`, **Public** - Streamlit Community Cloud's free tier needs a public repo or a connected account).
2. In the unzipped project folder:
```bash
git init
git add .
git commit -m "Initial commit: car rental NL-to-SQL assistant"
git branch -M main
git remote add origin https://github.com/<your-username>/car-rental-nl2sql.git
git push -u origin main
```
`.streamlit/secrets.toml` and `.cache/` are git-ignored, so your API key is never uploaded. If a key is ever committed by mistake, revoke it immediately.

## 2. Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. **Create app** -> choose your repository, branch `main`, main file path `app.py`.
3. Open **Advanced settings -> Secrets** and paste (from `.streamlit/secrets.toml.example`):
```toml
LLM_PROVIDER = "anthropic"
LLM_MODEL = "claude-sonnet-5-5"
ANTHROPIC_API_KEY = "your-real-key"
```
4. Click **Deploy**. The database file is part of the repo; if it were missing the app rebuilds it on start.

Without a key the app still opens: the Database, Guardrail and Evaluation tabs work, and the Ask tab asks for a key.

## 3. Run locally instead
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 4. After running the evaluation
```bash
python scripts/run_eval.py --provider anthropic
python scripts/make_report.py
git add results README.md && git commit -m "Add evaluation results" && git push
```
The app's **Evaluation** tab will then show your accuracy table and failure analysis.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: car_rental_sql` | Run commands from the project root |
| "No API key found" | Set the key in the sidebar, Secrets, or an environment variable |
| Model name rejected | Use a model name from your provider's current documentation |
| Streamlit Cloud build fails | Check `requirements.txt` is at the repo root and Python version is 3.10+ |
