from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
import requests
from models import News, Author, Comment, RedditPost, get_session, async_get_session, Base, engine, async_engine
from datetime import datetime



Base.metadata.create_all(bind=engine)

def scrap_gnews(kword:str, date_start:str, date_end:str, site:str=None):

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
    with get_session() as session:
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


async def scrap_reddit_links(kword:str, date_start:str, date_end:str, subreddit:str = ""):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
            locale='en-US',
        )
        page = await context.new_page()
        base_url = f"https://www.google.com/search?q=site:reddit.com/{subreddit}+{kword}+after:{date_start}+before:{date_end}&hl=en"
        start = 0

        async with await async_get_session() as session:

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
                    new_post = RedditPost(link=href)
                    await session.add(new_post)
                    print(f"Post created | Href: {href}")
                start += 10


async def scrap_reddit_post(post:RedditPost):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
            locale='en-US',
        )
        page = await context.new_page()
        await page.goto(post.link)

        async with async_get_session() as session:

            post_title = await page.locator("shreddit-post > h1").inner_text()
            post_content_raw = await page.locator("div.text-neutral-content").nth(0).locator("p").all()
            post_content = "\n".join([await paragraph.inner_text() for paragraph in post_content_raw]).strip()
            post_containers = await page.locator("div#-post-rtjson-content").all()
            post_date_raw = await page.locator("shreddit-post time").get_attribute("datetime")
            post_date = datetime.strptime(post_date_raw, "%Y-%m-%dT%H:%M:%S.%fZ")
            post_author = await page.locator("a.author-name").inner_text()
            author_obj = await Author.async_create_author_async(session, post_author)

            await post.async_add_info(
                session= session,
                title = post_title,
                content = post_content,
                date = post_date,

                author = author_obj,
            )

            for container in post_containers:
                comment_box = container.locator("xpath=../..") 
                comment_paragraphs = await container.locator("p").all()
                comment_author_locator = await comment_box.locator("a[aria-haspopup='dialog'][class='truncate font-bold text-neutral-content-strong text-12 hover:underline']").nth(0).text_content()
                comment_author = "".join([text.strip() for text in comment_author_locator if text.strip()])
                comment_content = "\n".join([await paragraph.inner_text() for paragraph in comment_paragraphs]).strip()
                comment_date_raw = await comment_box.locator("time").nth(0).get_attribute("datetime")
                comment_date = datetime.strptime(comment_date_raw, "%Y-%m-%dT%H:%M:%S.%fZ")

                await post.async_add_comment(session=session,
                                             comment=Comment(
                                                 author = author_obj,
                                                 post = post)
                                             )

        await browser.close()

asyncio.run(scrap_reddit_post())