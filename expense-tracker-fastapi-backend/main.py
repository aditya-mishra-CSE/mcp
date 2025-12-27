from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sqlite3
import json

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

app = FastAPI(title="Expense Tracker App")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  subcategory TEXT DEFAULT '',
                  note TEXT DEFAULT ''
            )
        """)


init_db()

class ExpenseCreate(BaseModel):
    date: str
    amount: float
    category: str
    subcategory: str | None = ""
    note: str | None = ""

@app.post("/expenses")
def add_expense(payload: ExpenseCreate):
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (payload.date, payload.amount, payload.category, payload.subcategory or "", payload.note or "")
        )
        c.commit()
        return {"status": "ok", "id": cur.lastrowid}


    
@app.get("/expenses")
def list_expenses(start_date, end_date):
    """List expense entries withan an inclusive data range."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("""SELECT id, date, amount, category, subcategory, note 
                        FROM expenses
                        WHERE date BETWEEN ? AND ?
                        ORDER BY id ASC
                        """,
                        (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@app.get("/expenses/summary")
def summarize(start_date, end_date, category=None):
    """Summarize expenses by category within an inclusive data range."""
    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += "AND category = ?"
            params.append(category)

        query += "GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
