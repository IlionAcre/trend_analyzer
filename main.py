from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
import requests
from models import News, Author, Comment, RedditPost, create_tables, wipe_database
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


async def scrap_reddit_links(async_session, kword:str, date_start:str, date_end:str, subreddit:str = None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
            locale='en-US',
        )
        page = await context.new_page()
        base_url = f"https://www.google.com/search?q=site:reddit.com/{subreddit+'/' if subreddit is not None else ''} {kword}+after:{date_start}+before:{date_end}&hl=en"
        start = 0
        post_warehouse = []

        async with async_get_session(async_session) as session:

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
                    new_post = RedditPost(link=href, subreddit=subreddit)
                    post_warehouse.append(new_post)
                    print(f"Post created | Href: {href}")
                start += 10

            session.add_all(post_warehouse)
            print(f"Committed {len(post_warehouse)} posts")


async def scrap_reddit_post(session, post: RedditPost):
    print(f"Scrapping {post.link}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0)',
            locale='en-US',
        )
        page = await context.new_page()
        await page.goto(post.link)

        post_warehouse = []
        comment_warehouse = []
        author_warehouse = []

        try:
            # Fetch post title and author
            post_title = await page.locator("shreddit-post > h1").inner_text()
            
            post_content_raw = await page.locator("div.text-neutral-content").nth(0).locator("p").all()
            post_content = "\n".join([await paragraph.inner_text() for paragraph in post_content_raw]).strip()

            post_date_raw = await page.locator("shreddit-post time").get_attribute("datetime")
            post_date = datetime.strptime(post_date_raw, "%Y-%m-%dT%H:%M:%S.%fZ")
            
            page.set_default_timeout(5000)
            try:
                post_author = await page.locator("a.author-name").inner_text()
            except Exception as e:
                post_author = "[Deleted]"

            # Use asynchronous create_author method or create a new one
            author = await Author.async_create_author(session, post_author)
            author_warehouse.append(author)

            # Add post info
            await post.async_add_info(
                title=post_title,
                content=post_content,
                date=post_date,
                author=author,
            )
            post_warehouse.append(post)

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
                    post=post,
                    content=comment_content,
                    date=comment_date
                )
                
                post.add_comment(new_comment)
                comment_warehouse.append(new_comment)

            session.add_all(author_warehouse)
            session.add_all(post_warehouse)
            session.add_all(comment_warehouse)
            print(f"Committing {len(post_warehouse)} posts")
            print(f"Committing {len(comment_warehouse)} comments")
            print("Committed all changes to the database")
        except Exception as e:
            print(f"Error processing post: {e}")

        await browser.close()

async def process_all_posts(async_session, keyword, s_date, e_date):

    async with async_get_session(async_session) as session:
        await scrap_reddit_links(async_session, keyword, s_date, e_date)

        all_posts = await RedditPost.async_get_all_posts(session)
        print(f"Got a total of {len(all_posts)} items")
        tasks = [scrap_reddit_post(session, post) for post in all_posts]
        await asyncio.gather(*tasks)


KEYWORD = "Ubisoft"
S_DATE = "2022-10-10"
E_DATE = "2022-10-11"
db_details = initialize_db(KEYWORD)
wipe_database(db_details["engine"])
create_tables(db_details["engine"])
current_session = db_details["SessionLocal"]
current_async_session = db_details["SessionLocalAsync"]
scrap_gnews(current_session, KEYWORD, S_DATE, E_DATE)
asyncio.run(process_all_posts(current_async_session, KEYWORD, S_DATE, E_DATE))