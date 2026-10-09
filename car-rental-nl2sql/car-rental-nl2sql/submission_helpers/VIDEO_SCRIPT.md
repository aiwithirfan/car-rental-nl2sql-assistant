# Video walkthrough script (target 7-8 minutes, narrate in your own words)

Record your screen with your voice (OBS Studio, Zoom or Loom). These are talking points, not a text to read out.

| Time | Show on screen | Say (in your own words) |
|---|---|---|
| 0:00-0:45 | README top | Who the client is, the problem (managers cannot write SQL), the goal, and the stack (SQLite + LLM API + Streamlit) |
| 0:45-1:30 | `docs/SCOPE.md` | What is in/out of scope; the success targets you set before building |
| 1:30-2:30 | App -> Database tab | 7 tables, 5,896 rows, foreign keys; why the data is synthetic and frozen at 2025-12-31 |
| 2:30-4:00 | App -> Ask tab | Run 3 questions (easy, medium, hard). Show the SQL, the result, the attempts expander; show a retry fixing an error if one happens |
| 4:00-5:15 | App -> Guardrail demo | Run `DELETE FROM customers`, a stacked statement, `sqlite_master`, and the cross join. Explain each layer (validator, read-only connection, authorizer, timeout) |
| 5:15-6:30 | Evaluation tab / `results/` | Accuracy by difficulty, failure types, how result sets (not SQL text) are compared |
| 6:30-7:30 | Ablation table | What you removed/swapped, the exact accuracy cost, which failures appeared and why |
| 7:30-8:00 | README limitations | One limitation, one thing you would improve, what you learned and which AI suggestions you corrected |

Tips: say what *you* decided and why, show a real failure honestly, and keep the tone calm and professional.
