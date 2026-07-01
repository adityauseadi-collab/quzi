# QuizMaster Pro

A production-ready Online Quiz Management System built with Python Flask.

## Features

### Admin
- Dashboard with live stats (students, questions, quizzes, avg score)
- Full question bank: add, edit, delete, search, filter by category
- Bulk import questions from Excel (.xlsx) or CSV
- Create quizzes with category, question count, time limit
- Publish / disable quizzes
- Student management (activate/deactivate)
- Analytics with Chart.js charts

### Student
- Dashboard with available quizzes and progress chart
- Timed quiz interface with question navigation
- Auto-submit when timer expires
- Instant results with grade (A+/A/B/C/D/F)
- Full answer review with correct/wrong indicators
- PDF result download
- Leaderboard

### Tech Stack
- **Backend**: Python Flask, SQLAlchemy, Flask-Login, Flask-WTF
- **Database**: SQLite (swap to PostgreSQL via DATABASE_URL)
- **Frontend**: Bootstrap 5, Chart.js, Glassmorphism CSS
- **Import**: Pandas + openpyxl
- **PDF**: ReportLab
- **Tests**: pytest (61 tests)

---

## Quick Start

```bash
git clone <repo>
cd quizmaster
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

### Demo Credentials old
| Role    | Username  | Password     |
|---------|-----------|--------------|
| Admin   | admin     | admin123     |
| Student | student   | student123   |

---new

| Role    | Username  | Password       |
| ------- | --------- | -------------- |
| Admin   | `admin`   | `Admin@2026`   |
| Teacher | `teacher` | `Teacher@2026` |
| Student | `student` | `Student@2026` |


## Project Structure

```
quizmaster/
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── routes/          # Flask blueprints
│   ├── services/        # Business logic
│   ├── forms/           # WTForms
│   ├── templates/       # Jinja2 HTML
│   ├── static/          # CSS, JS, images
│   ├── tests/           # pytest suite
│   └── utils/           # Helpers
├── config.py
├── app.py               # Entry point
└── requirements.txt
```

---

## Import Format

Upload `.xlsx` or `.csv` with these columns:

| Question | OptionA | OptionB | OptionC | OptionD | CorrectAnswer | Category | Difficulty | Explanation |
|----------|---------|---------|---------|---------|---------------|----------|------------|-------------|

- `CorrectAnswer` must be `A`, `B`, `C`, or `D`
- `Category`, `Difficulty`, `Explanation` are optional

Download the sample file from Admin → Import.

---

## Running Tests

```bash
python -m pytest app/tests/ -v
```

---

## Deployment

### Render / Railway
1. Set `DATABASE_URL` to a PostgreSQL connection string
2. Set `SECRET_KEY` to a random secret
3. Set `FLASK_ENV=production`
4. Start command: `gunicorn app:app`

### PythonAnywhere
1. Upload files and install requirements in a virtualenv
2. Set WSGI file to point to `app:app`
3. Set environment variables in the web tab

### Environment Variables

```
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite:///instance/quizmaster.db
FLASK_ENV=development
```

---

## Grading Scale

| Score   | Grade |
|---------|-------|
| 90-100% | A+    |
| 80-89%  | A     |
| 70-79%  | B     |
| 60-69%  | C     |
| 50-59%  | D     |
| < 50%   | F     |
