# Resume framing — Smart Study Tracker

These are drop-in versions of the project line for a Data Analyst (AI) resume.
Pick the variant that matches the slot you're filling, then **replace every italicised number with the actual value** from your data — recruiters notice when numbers look generic.

---

## Long-form (4–5 bullet "Projects" entry)

**Smart Study Tracker** — Python · MySQL · scikit-learn · pandas · VADER · Tkinter
*GitHub: github.com/<your-username>/smart-study-tracker*

- Designed and shipped an end-to-end study analytics tool with a 5-table MySQL schema (*~12* analytical SQL queries, including a recursive CTE that fills missing-day gaps in the daily-progress series).
- Engineered a feature pipeline in **pandas** — rolling 7-day windows, recency gaps, day-of-week, hour-of-day — and trained a **scikit-learn `Pipeline`** (`StandardScaler` + `OneHotEncoder` → `LogisticRegression`, `class_weight="balanced"`) that flags low-focus risk on upcoming sessions with **~*81%* test accuracy**.
- Integrated **VADER sentiment analysis** on free-text session notes and validated its signal with a Pearson correlation of **r = *+0.34* (p < *0.05*)** between note sentiment and hours studied.
- Authored a **pandas / seaborn EDA notebook** (`notebooks/analysis.ipynb`) covering daily trends, mood × productivity, sentiment distribution, and weekday patterns.
- Hardened the repo for review: env-var-only secrets via `python-dotenv`, idempotent schema migrations on startup, GitHub Actions CI (`ruff` + `py_compile` matrix on Python 3.10–3.12), MIT-licensed.

---

## Mid-length (3 bullets, sized for a one-page resume)

**Smart Study Tracker — Python · MySQL · scikit-learn · pandas · VADER**
*github.com/<your-username>/smart-study-tracker*

- Built an end-to-end study analytics app on a 5-table MySQL schema (*1k+* session rows, *12+* analytical queries) with a Tkinter dashboard rendering custom canvas charts for daily trends and subject mix.
- Trained a scikit-learn logistic-regression pipeline on engineered features (rolling 7-day hours, recency gap, mood, sentiment) achieving **~*81%* accuracy** in flagging low-focus sessions; surfaced predictions live in the UI.
- Validated note sentiment as a productivity signal using **VADER** + scipy stats (Pearson **r = *+0.34*, p < *0.05***), then published a pandas/seaborn EDA notebook walking the full analysis.

---

## Short (2 bullets, for a "Selected Projects" line in an Experience-heavy resume)

- **Smart Study Tracker** *(Python, MySQL, scikit-learn, pandas, VADER)* — End-to-end app on a 5-table schema; trained a logistic-regression focus-risk classifier (*81%* test accuracy) and integrated VADER sentiment scoring (Pearson r = *+0.34* with hours studied). [github.com/<your-username>/smart-study-tracker](https://github.com/)
- Authored a pandas/seaborn EDA notebook covering mood × productivity, sentiment distribution, and weekday patterns; hardened the repo with env-var secrets, idempotent schema migrations, and GitHub Actions CI.

---

## Tagline (LinkedIn "Featured" / portfolio site card)

> Python desktop app that turns study sessions into AI-driven coaching.
> 5-table MySQL schema · pandas feature engineering · scikit-learn focus-risk classifier · VADER sentiment on free-text notes · Jupyter EDA notebook.

---

## Numbers checklist — fill these in before sending

Run these once you have ~30+ sessions logged so the numbers are honest.

| Slot | How to get the number |
|---|---|
| `~12 analytical queries` | Count `cursor.execute` calls in `tracker_utils.py` (currently 14). |
| `1k+ session rows` | `SELECT COUNT(*) FROM study_sessions;` |
| `~81% test accuracy` | Output of `python -m ml.train --user-id <id>`. |
| `Pearson r = +0.34` | The `pearsonr` cell in `notebooks/analysis.ipynb`. |
| `p < 0.05` | Same cell — quote whichever bracket is true (`< 0.05`, `< 0.01`, etc.). |
| Weekly attainment % | `daily_hours / goal_hours` averaged over a month. |

---

## Interview talking points (so you can defend each bullet)

1. **"Why VADER instead of a transformer?"**
   Notes are short, informal, and sometimes use slang ("doomscrolled again"). VADER is rule-based, ships with no model download, and runs in microseconds — fine for the volume here. A transformer would be over-engineering until the corpus gets bigger and more nuanced.

2. **"What was the label for the focus-risk classifier?"**
   A heuristic: low-focus = mood ∈ {Stressed, Tired} OR sentiment ≤ -0.2; high-focus = mood = Focused AND sentiment ≥ 0. Rows that fit neither are dropped to keep the signal clean. This is honest about the proxy nature of the label and a good place to talk about label leakage and how I'd improve it (e.g., next-day mood as the outcome).

3. **"Why logistic regression over a tree-based model?"**
   With only ~30–100 rows per user, a tree-based model would memorise. Logistic regression with `class_weight="balanced"` and a simple feature set generalises better at this scale, and the coefficients stay interpretable — which matters for a personal-coaching app.

4. **"Class imbalance?"**
   Fewer Stressed/Tired rows than Focused/Happy. Handled with `class_weight="balanced"` in `LogisticRegression`. I also report per-class precision/recall in `metrics["report"]`, not just overall accuracy.

5. **"How would you scale this to 10,000 users?"**
   Move MySQL writes behind a thin API, batch-train the classifier nightly with a per-user model registry (S3 + a `latest` pointer), serve predictions from a cached pipeline, and replace VADER with a fine-tuned DistilBERT once the note corpus is large enough.
