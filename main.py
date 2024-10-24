from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
import requests
from models import News, Author, Comment, RedditPost, Link, create_tables, wipe_database
from db_manager import get_session, async_get_session, create_db, create_engine_and_sessions
from sqlalchemy.future import select
from datetime import datetime


def initialize_db(db_name: str):
    create_db(db_name)
    db_connections = create_engine_and_sessions(db_name)
    create_tables(db_connections['engine'])
    return db_connections


def scrap_gnews(sync_session, kword:str, date_start:str, date_end:str, site:str=None):

    """
    Used to extract news from google and pass them into my existing DB
    
    Args:
    kword(string): The keyword to search for. What you put in the google's search bar.
    date_start(string): Start date for the date range.
    date_end(string): End date for the date range.
    site(string): Url for the website if targeted search is needed. Default: None.
    """

    if site is not None:
        link = f"https://news.google.com/search?q=site%3A{site}%20{kword}%20after%3A{date_start}%20before%3A{date_end}&hl=en-US&gl=US&ceid=US%3Aen"
    else:    
        link = f"https://news.google.com/rss/search?q={kword}%20after%3A{date_start}%20before%3A{date_end}&hl=en-US&gl=US&ceid=US%3Aen"
    with get_session(sync_session) as session:
        response = requests.get(link)
        soup=BeautifulSoup(response.content , "lxml-xml")
        items = soup.find_all("item")

        for item in items:
            item_headline = item.find("title").text.strip().rsplit(' - ', 1)
            item_title = item_headline[0].strip()
            item_publisher = item_headline[1].strip()
            item_link = item.find("link").text
            item_date_raw = item.find("pubDate").text.replace("GMT", "").strip()
            item_date = datetime.strptime(item_date_raw, "%a, %d %b %Y %H:%M:%S")
            item_source = item.find("source").text

            new_new = News(
                title=item_title,
                publisher = item_publisher,
                link = item_link,
                date =  item_date,
                source =  item_source,
            )

            session.add(new_new)


async def scrap_reddit_links(session, page, kword:str, date_start:str, date_end:str, subreddit:str = None):
    base_url = f"https://www.google.com/search?q=site:reddit.com/{subreddit+'/' if subreddit is not None else ''} {kword}+after:{date_start}+before:{date_end}&hl=en"
    start = 0
    post_warehouse = []
    seen_links = set()

    while True:
        search_url = f"{base_url}&start={start:02d}"
        print(f"Fetching: {search_url}")
        
        await page.goto(search_url)
        if await page.locator('p[aria-level="3"]').is_visible():
            print("No results found. Stopping.")
            break
        posts = await page.locator("a[jsname='UWckNb']").all()
        for post in posts:
            href = await post.get_attribute("href")
            if href not in seen_links:
                new_link = Link(link=href)
                post_warehouse.append(new_link)
                seen_links.add(href)
                print(f"Post created | Href: {href}")
            else:
                print(f"Duplicate found | Href: {href}")
        start += 10

    session.add_all(post_warehouse)
    print(f"Committed {len(post_warehouse)} posts")


MAX_CONTENT_LENGTH = 200
async def scrap_reddit_post(session, page, link : Link):
    print(f"Scrapping {link.link}")
    await page.goto(link.link)

    post_warehouse = []
    comment_warehouse = []

    try:
        # Fetch post title and author
        post_title = await page.locator("shreddit-post > h1").inner_text()
        
        post_content_raw = await page.locator("div.text-neutral-content").nth(0).locator("p").all()
        post_content = "\n".join([await paragraph.inner_text() for paragraph in post_content_raw]).strip()
        if len(post_content) > MAX_CONTENT_LENGTH:
            post_content= post_content[:MAX_CONTENT_LENGTH] + '...'
        else:
            post_content= post_content
        post_date_raw = await page.locator("shreddit-post time").get_attribute("datetime")
        post_date = datetime.strptime(post_date_raw, "%Y-%m-%dT%H:%M:%S.%fZ")
        
        page.set_default_timeout(5000)
        try:
            post_author = await page.locator("a.author-name").inner_text()
        except Exception as e:
            post_author = "[Deleted]"

        # Use asynchronous create_author method or create a new one
        author = await Author.async_create_author(session, post_author)
        session.commit()
        # Add post info
        new_post = RedditPost(
            title=post_title,
            content=post_content,
            date=post_date,
            author=author,
            link=link,
        )
        post_warehouse.append(new_post)

        # Collect comments
        post_containers = await page.locator("div#-post-rtjson-content").all()
        for container in post_containers:
            comment_box = container.locator("xpath=../..")
            comment_paragraphs = await container.locator("p").all()
            comment_content = "\n".join([await paragraph.inner_text() for paragraph in comment_paragraphs]).strip()
            comment_date_raw = await comment_box.locator("time").nth(0).get_attribute("datetime")
            comment_date = datetime.strptime(comment_date_raw, "%Y-%m-%dT%H:%M:%S.%fZ")
            try:
                comment_author_locator = await comment_box.locator("a[aria-haspopup='dialog'][class='truncate font-bold text-neutral-content-strong text-12 hover:underline']").nth(0).text_content()
                comment_author = "".join([text.strip() for text in comment_author_locator if text.strip()])
            except:
                comment_author = "[Deleted]"
            comment_author = await Author.async_create_author(session, comment_author)

            new_comment = Comment(
                author=comment_author,
                post=new_post,
                content=comment_content,
                date=comment_date
            )
            session.add(new_comment)
            session.commit()
            new_post.add_comment(new_comment)
            session.commit()
        session.add(new_post)
        session.commit()
        print(f"Committing {len(post_warehouse)} posts")
        print(f"Committing {len(comment_warehouse)} comments")
        print("Committed all changes to the database")
        

    except Exception as e:
        print(f"Error processing post: {e}")
        print("Session rolled back")


async def limited_scrap_reddit_post(session, page, post, semaphore):
    async with semaphore:
        try:
            await scrap_reddit_post(session, page, post)
        finally:
            await page.close()

async def process_all_posts(async_session_maker, keyword, s_date, e_date):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        async with async_get_session(async_session_maker) as session:
            page = await browser.new_page()
            await scrap_reddit_links(session, page, keyword, s_date, e_date)
            print("STARTING NEXT FUNCTION")
            all_posts = await Link.async_get_all_posts(session)
            print(f"Got a total of {len(all_posts)} items")
          
            for post in all_posts:
                await scrap_reddit_post(session, page, post)
            await page.close() 
            await session.commit()
            print(f"Committed {len(all_posts)} posts.")

        await browser.close()

KEYWORD = "Ubisoft"
S_DATE = "2022-10-16"
E_DATE = "2022-10-17"
db_details = initialize_db(KEYWORD)
# wipe_database(db_details["engine"])
# create_tables(db_details["engine"])
current_session = db_details["SessionLocal"]
current_async_session = db_details["SessionLocalAsync"]
# scrap_gnews(current_session, KEYWORD, S_DATE, E_DATE)
asyncio.run(process_all_posts(current_async_session, KEYWORD, S_DATE, E_DATE))