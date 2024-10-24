from contextlib import contextmanager, asynccontextmanager
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from typing import Dict
from sqlalchemy import create_engine
import os

load_dotenv()


@asynccontextmanager
async def async_no_autoflush(session: AsyncSession):
    previous_autoflush = session.autoflush
    session.autoflush = False  # Disable autoflush for this context
    try:
        yield
    finally:
        session.autoflush = previous_autoflush 


@contextmanager
def get_session(SessionLocal: sessionmaker):
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()


@asynccontextmanager
async def async_get_session(SessionLocalAsync: sessionmaker):
    async_session = SessionLocalAsync()
    try:
        yield async_session
        await async_session.commit()
    except Exception as e:
        print(f"This ocurred:\n{e}")
    finally:
        await async_session.close()


def get_credentials() -> Dict[str, str]:
    return {
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASSWORD"),
        'host': os.getenv("DB_HOST", "localhost"),
        'port': os.getenv("DB_PORT", "5432")
    }


def create_engine_and_sessions(db_name: str = None) -> Dict[str, Engine | sessionmaker]:
    """
    Dynamically create engines and session factories for both sync and async usage.
    If db_name is not provided, it defaults to the value from environment variables.
    """
    credentials = get_credentials()
    
    db_name = db_name or os.getenv("DB_NAME")

    DATABASE_URL = f'postgresql://{credentials["user"]}:{credentials["password"]}@{credentials["host"]}:{credentials["port"]}/{db_name}'
    ASYNC_DATABASE_URL = f'postgresql+asyncpg://{credentials["user"]}:{credentials["password"]}@{credentials["host"]}:{credentials["port"]}/{db_name}'

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    async_engine = create_async_engine(ASYNC_DATABASE_URL)
    SessionLocalAsync = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

    return {
        'engine': engine,
        'async_engine': async_engine,
        'SessionLocal': SessionLocal,
        'SessionLocalAsync': SessionLocalAsync
    }


def create_db(db_name: str):
    credentials = get_credentials()

    conn = None
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=credentials['user'],
            password=credentials['password'],
            host=credentials['host'],
            port=credentials['port']
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
        print(f"Database '{db_name}' created successfully!")
        cur.close()
    except psycopg2.DatabaseError as e:
        print(f"Error: {e}")
    finally:
        if conn is not None:
            conn.close()


