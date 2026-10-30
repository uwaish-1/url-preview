# Simple URL Preview App

A simple full-stack internship assignment.

## What it does

1. User creates an account.
2. User logs in.
3. User enters a website URL.
4. FastAPI uses Playwright to open the website and take a screenshot.
5. The URL and screenshot are saved in SQLite.
6. React displays all saved previews.
7. User can delete saved previews.

## Tech stack

- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite
- Screenshot: Playwright
- Authentication: JWT

## Project structure

```text
url-preview-app/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── previews/
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Signup.jsx
│   │   │   └── Dashboard.jsx
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## Run backend

Open a terminal:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload
```

Backend:
http://localhost:8000

API documentation:
http://localhost:8000/docs

## Run frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:
http://localhost:5173

## Important

Start the backend first, then start the frontend.

This project is intentionally kept simple so the complete request flow is easy to understand and explain in an internship interview.
