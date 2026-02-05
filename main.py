import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor

load_dotenv()

app = FastAPI(title="Railway FastAPI Demo")


def _normalize_db_url(url: str | None) -> str | None:
    if url and url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _get_db_url() -> str:
    url = _normalize_db_url(os.getenv("DATABASE_URL"))
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


@contextmanager
def _get_conn():
    url = _get_db_url()
    conn = psycopg2.connect(url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_db():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS demo_items (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    payload TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


@app.on_event("startup")
def on_startup():
    try:
        _init_db()
    except Exception as exc:
        # Allow app to start even if DB isn't configured yet.
        print(f"DB init skipped: {exc}")


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI on Railway"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/echo/{text}")
def echo(text: str):
    return {"echo": text}


@app.get("/items/create")
def create_item(name: str, payload: str | None = None):
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO demo_items (name, payload)
                    VALUES (%s, %s)
                    RETURNING id, name, payload, created_at
                    """,
                    (name, payload),
                )
                row = cur.fetchone()
                return dict(row)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/items/{item_id}")
def get_item(item_id: int):
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, payload, created_at
                    FROM demo_items
                    WHERE id = %s
                    """,
                    (item_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Item not found")
                return dict(row)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
