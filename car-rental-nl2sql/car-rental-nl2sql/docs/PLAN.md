# Week 4 Plan (5 lines)

1. **Skill focus:** text-to-SQL with LLM APIs and defensive engineering (SQLite, validators, authorizers) - new compared with earlier weeks.
2. **Learn (30-45 min):** how schema prompts, few-shot error feedback and read-only SQL validation work; SQLite `mode=ro`, authorizer and progress-handler APIs.
3. **Build:** 7-table database (3,000+ rows) -> 50 questions with gold SQL -> pipeline (schema prompt, validator, retry) -> Streamlit app.
4. **Measure:** execution accuracy by difficulty, failure types, 13 unsafe-request tests, and an ablation of retry / schema richness / model.
5. **Measurable target:** **at least 80% overall execution accuracy on the 50 questions and 13/13 unsafe requests blocked**, with all evidence committed.
