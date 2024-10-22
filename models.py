import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, create_engine
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

load_dotenv()


@contextmanager
def get_session(SessionLocal):
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()

@asynccontextmanager
async def async_get_session(SessionLocalAsync):
    async_session = SessionLocalAsync()
    try:
        yield async_session
        await async_session.commit()
    except Exception as e:
        await async_session.rollback()
    finally:
        await async_session.close()

def create_engine_and_sessions(db_name=None):
    """
    Dynamically create engines and session factories for both sync and async usage.
    If db_name is not provided, it defaults to the value from environment variables.
    """
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")

    db_name = db_name or os.getenv("DB_NAME")

    DATABASE_URL = f'postgresql://{user}:{password}@{host}:{port}/{db_name}'
    ASYNC_DATABASE_URL = f'postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}'

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

def create_db(db_name, user, password, host="localhost", port="5432"):

    conn = None

    try:
        conn = psycopg2.connect(
            dbname= "postgres",
            user=user,
            password=password,
            host=host,
            port=port
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

Base = declarative_base()

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    publisher = Column(String, index=True)
    link = Column(String, index=True, unique=True)
    date =  Column(DateTime, index=True)
    source =  Column(String, index=True)

    def __repr__(self):
        formatted_date = self.date.strftime("%a, %d %b %Y %H:%M:%S") if self.date else 'No Date'
        return f"<{self.title} from {self.publisher} on {formatted_date})>"
    
# if __name__ == "__main__":
#     create_db(os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD"), os.getenv("DB_HOST"), os.getenv("DB_PORT"))

class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    
    posts = relationship("RedditPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")

    @classmethod
    def create_author(cls, session: Session, name: str):
        author = session.query(cls).filter_by(name=name).first()
        if author:
            return author
        else:
            new_author = cls(name=name)
            session.add(new_author)
            return new_author
        
    @classmethod
    async def async_create_author_async(cls, session: AsyncSession, name: str):
        result = await session.execute(select(cls).filter_by(name=name))
        author = result.scalar_one_or_none()
        
        if author:
            return author
        else:
            new_author = cls(name=name)
            await session.add(new_author)
            return new_author
        
    def __repr__(self):
        return self.name

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, index=True)

    post_id = Column(Integer, ForeignKey('rposts.id'))
    author_id = Column(Integer, ForeignKey('authors.id'))

    post = relationship("RedditPost", back_populates="comments")
    author = relationship("Author", back_populates="comments")

    def __repr__(self):
        return f"{self.author.name} commented:\n{self.content}"

class RedditPost(Base):
    __tablename__ = "rposts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String, index=True)
    subreddit = Column(String, index=True)
    date = Column(DateTime, index=True)
    link = Column(String, index=True, unique=True)

    author_id = Column(Integer, ForeignKey('authors.id'))

    author = relationship("Author", back_populates="posts")
    comments = relationship("Comment", back_populates="post")

    def add_info(self, session, **kw):
        """
        Modify the current RedditPost instance's attributes using **kw.
        """
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"RedditPost has no attribute '{key}'")

        session.add(self)

    async def async_add_info(self, session, **kw):
        """
        Modify the current RedditPost instance's attributes using **kw.
        """
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"RedditPost has no attribute '{key}'")

        await session.add(self)
            
    def add_comment(self, comment, session):
        self.comments.append(comment)
        session.add(comment)

    async def async_add_comment(self, comment, session: AsyncSession):
        self.comments.append(comment)
        await session.add(comment)

    @classmethod
    def get_all_posts(cls, session: Session):
        return session.query(cls).all()
    
    @classmethod
    async def async_get_all_posts(cls, session: AsyncSession):
        result = await session.execute(select(cls))
        return result.scalars().all()


    def __repr__(self):
        formatted_date = self.date.strftime("%a, %d %b %Y %H:%M:%S") if self.date else 'No Date'
        return f"<{self.title} from {self.author} on {formatted_date})>"