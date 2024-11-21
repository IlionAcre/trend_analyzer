from contextlib import contextmanager, asynccontextmanager
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from typing import Dict
from sqlalchemy import create_engine, func, Table, text
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
        'db_name' : os.getenv("DB_NAME"),
        'password': os.getenv("DB_PASSWORD"),
        'host': os.getenv("DB_HOST", "localhost"),
        'port': os.getenv("DB_PORT", "5432")
    }


def create_engine_and_sessions(user: str = None) -> Dict[str, Engine | sessionmaker]:
    """
    Dynamically create engines and session factories for both sync and async usage.
    If schema_name is not provided, it defaults to the value from environment variables.
    """
    credentials = get_credentials()

    user = user.lower()
    DATABASE_URL = f'postgresql://{user}:{credentials["password"]}@{credentials["host"]}:{credentials["port"]}/{credentials["db_name"]}'
    ASYNC_DATABASE_URL = f'postgresql+asyncpg://{user}:{credentials["password"]}@{credentials["host"]}:{credentials["port"]}/{credentials["db_name"]}'

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


def filter_data_by_date(session, model, start_date, end_date, date_column='date'):
    """
    Filter data based on date range and return the filtered result.

    Parameters:
    session: SQLAlchemy session to execute the query.
    model: The SQLAlchemy model representing the table to filter.
    start_date (str): The start date for filtering data.
    end_date (str): The end date for filtering data.
    date_column (str): The name of the date column to filter by (default is 'date').

    Returns:
    list: A list of filtered data entries from the specified model.
    """
    # Perform initial query with date range filter
    date_field = model.c[date_column] if isinstance(model, Table) else getattr(model, date_column)
    filtered_query = session.query(model).filter(
        date_field >= start_date,
        date_field <= end_date
    )
    filtered_data = filtered_query.all()

    # If no data found, find closest matching dates
    if not filtered_data:
        closest_start = session.query(date_field).order_by(
            func.abs(func.extract('epoch', date_field - start_date))
        ).first()[0]
        closest_end = session.query(date_field).order_by(
            func.abs(func.extract('epoch', date_field - end_date))
        ).first()[0]

        # Query again using the closest available dates
        filtered_data = session.query(model).filter(
            date_field >= closest_start,
            date_field <= closest_end
        ).all()

    return filtered_data


def set_schema(session, schema_name: str):
    """
    Set the schema for the current database session.

    This function modifies the search path for the given SQLAlchemy session to target the specified schema,
    allowing all subsequent queries to be executed in the context of that schema.

    Parameters:
    session (Session): The SQLAlchemy session in which to set the schema.
    schema_name (str): The name of the schema to set as the search path.

    """
    session.execute(text(f"SET search_path TO {schema_name}_schema;"))