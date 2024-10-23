from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine


Base = declarative_base()


def create_tables(engine):
    Base.metadata.create_all(bind=engine)
    print("Tables created!")


async def async_create_tables(async_engine: AsyncEngine):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def wipe_database(engine):
    Base.metadata.drop_all(bind=engine)
    print("Database wiped successfully!")


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    publisher = Column(String, index=True)
    date =  Column(DateTime, index=True)
    source =  Column(String, index=True)
    link = Column(String, index=True, unique=True)

    def __repr__(self):
        formatted_date = self.date.strftime("%a, %d %b %Y %H:%M:%S") if self.date else 'No Date'
        return f"<{self.title} from {self.publisher} on {formatted_date})>"
    

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
    # Use async execute for async queries
        result = await session.execute(select(Author).where(Author.name == name))
        author = result.scalar_one_or_none()  # Get the author or None
        if author is None:
            author = Author(name=name)
        return author
        
    def __repr__(self):
        return self.name


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, index=True)
    date = Column(DateTime, index=True)

    post_id = Column(Integer, ForeignKey('rposts.id'))
    author_id = Column(Integer, ForeignKey('authors.id'))

    post = relationship("RedditPost", back_populates="comments", lazy="selectin")
    author = relationship("Author", back_populates="comments", lazy="selectin")

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

    author = relationship("Author", back_populates="posts", lazy="selectin")
    comments = relationship("Comment", back_populates="post", lazy="selectin")

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

    async def async_add_info(self, **kw):
        """
        Modify the current RedditPost instance's attributes using **kw.
        """
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"RedditPost has no attribute '{key}'")
            
    def add_comment(self, comment):
        self.comments.append(comment)

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