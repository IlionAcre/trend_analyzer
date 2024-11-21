from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.exc import IntegrityError
from db_manager import async_no_autoflush

Base = declarative_base()


def create_tables(engine):
    """
    Create all tables in the database.

    Parameters:
    engine: SQLAlchemy engine to connect to the database.

    Returns:
    None
    """
    Base.metadata.create_all(bind=engine)
    print("Tables created!")


async def async_create_tables(async_engine: AsyncEngine) -> None:
    """
    Asynchronously create all tables in the database.

    Parameters:
    async_engine (AsyncEngine): SQLAlchemy async engine to connect to the database.

    Returns:
    None
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def wipe_database(engine) -> None:
    """
    Drop all tables in the database.

    Parameters:
    engine: SQLAlchemy engine to connect to the database.

    Returns:
    None
    """
    Base.metadata.drop_all(bind=engine)
    print("Database wiped successfully!")


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    publisher = Column(String)
    date = Column(DateTime)
    source = Column(String)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)
    keywords = Column(String, nullable=True)
    link = Column(String, unique=True)

    def __repr__(self) -> str:
        formatted_date = self.date.strftime("%a, %d %b %Y %H:%M:%S") if self.date else 'No Date'
        return f"<{self.title} from {self.publisher} on {formatted_date})>"


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    link = Column(String, unique=True)
    post = relationship("RedditPost", back_populates="link", lazy="selectin")

    @classmethod
    async def async_get_all_posts(cls, session: AsyncSession):
        result = await session.execute(select(cls))
        return result.scalars().all()

    def __repr__(self) -> str:
        return f"<{self.link})>"


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    posts = relationship("RedditPost", back_populates="author", lazy="selectin")
    comments = relationship("Comment", back_populates="author", lazy="selectin")

    @classmethod
    def create_author(cls, session: Session, name: str):
        result = session.execute(select(Author).where(Author.name == name))
        author = result.scalar_one_or_none()
        if author is None:
            author = Author(name=name)
        return author

    @classmethod
    async def async_create_author(cls, session: AsyncSession, name: str):
        try:
            previous_autoflush = session.autoflush
            session.autoflush = False

            result = await session.execute(select(Author).where(Author.name == name))
            author = result.scalar_one_or_none()

            if author is None:
                author = Author(name=name)
                session.add(author)
                await session.commit()

            session.autoflush = previous_autoflush

            return author

        except IntegrityError:
            await session.rollback()
            # Query again in case the author was created by another process
            result = await session.execute(select(Author).where(Author.name == name))
            author = result.scalar_one_or_none()
            return author


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    date = Column(DateTime)
    post_id = Column(Integer, ForeignKey('rposts.id'), index=True)
    author_id = Column(Integer, ForeignKey('authors.id'), index=True)

    post = relationship("RedditPost", back_populates="comments", lazy="selectin")
    author = relationship("Author", back_populates="comments", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.author.name} commented:\n{self.content}"


class RedditPost(Base):
    __tablename__ = "rposts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    subreddit = Column(String)
    date = Column(DateTime)
    author_id = Column(Integer, ForeignKey('authors.id'), index=True)
    link_id = Column(Integer, ForeignKey('links.id'), index=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)
    keywords = Column(String, nullable=True)

    author = relationship("Author", back_populates="posts", lazy="selectin")
    comments = relationship("Comment", back_populates="post", lazy="selectin")
    link = relationship("Link", back_populates="post", lazy="selectin")

    def add_info(self, session: Session, **kw) -> None:
        """
        Modify the current RedditPost instance's attributes using **kw.
        """
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"RedditPost has no attribute '{key}'")

        session.add(self)

    async def async_add_info(self, **kw) -> None:
        """
        Asynchronously modify the current RedditPost instance's attributes using **kw.
        """
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"RedditPost has no attribute '{key}'")

    def add_comment(self, comment) -> None:
        self.comments.append(comment)

    async def async_add_comment(self, comment, session: AsyncSession) -> None:
        self.comments.append(comment)
        await session.add(comment)

    @classmethod
    def get_all_posts(cls, session: Session):
        return session.query(cls).all()

    @classmethod
    async def async_get_all_posts(cls, session: AsyncSession):
        result = await session.execute(select(cls))
        return result.scalars().all()

    def __repr__(self) -> str:
        formatted_date = self.date.strftime("%a, %d %b %Y %H:%M:%S") if self.date else 'No Date'
        return f"<{self.title} from {self.author} on {formatted_date})>"
