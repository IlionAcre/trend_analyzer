from transformers import pipeline
from rake_nltk import Rake
from nltk.tokenize import word_tokenize
from models import RedditPost, News
from db_manager import create_engine_and_sessions, get_session
from typing import List, Tuple

# Initialize Rake for keyword extraction
r = Rake(max_length=4, word_tokenizer=word_tokenize, include_repeated_phrases=False)

def analyze_sentiments(text_type: str, elements: List[str]) -> Tuple[float, str]:
    """
    Analyze the sentiments of a list of text elements.

    Parameters:
    text_type (str): "text" or "news" to control which model is used for the analysis.
    elements (List[str]): The list of elements to be analyzed.

    Raises:
    ValueError: If the text_type is neither "text" nor "news".

    Returns:
    Tuple[float, str]: The average sentiment score and overall sentiment label.
    """
    device = "cuda"
    model = "ProsusAI/finbert" if text_type == "news" else "Falcontreras/Tiny_Sentiment_Tunning" if text_type == "text" else None
    if model is None:
        raise ValueError("Invalid text_type")
    
    pipe = pipeline("text-classification", model=model, device=device)

    total_score = 0
    
    for element in elements:
        sentiment = pipe(element)
        label = sentiment[0]["label"]
        score = sentiment[0]["score"]
        if label in ["LABEL_1", "positive"]:
            total_score += score
        elif label in ["LABEL_0", "negative"]:
            total_score -= score

    total_sentiment = "positive" if total_score > 0 else "negative"
    total_score = total_score / len(elements)

    return total_score, total_sentiment


def analyze_sentiment(text_type: str, element: str) -> Tuple[float, str]:
    """
    Analyze the sentiment of a single text element.

    Parameters:
    text_type (str): "text" or "news" to control which model is used for the analysis.
    element (str): The text element to be analyzed.

    Raises:
    ValueError: If the text_type is neither "text" nor "news".

    Returns:
    Tuple[float, str]: The sentiment score and sentiment label.
    """
    device = "cuda"
    model = "ProsusAI/finbert" if text_type == "news" else "Falcontreras/Tiny_Sentiment_Tunning" if text_type == "text" else None
    if model is None:
        raise ValueError("Invalid text_type")
    
    pipe = pipeline("text-classification", model=model, device=device)

    total_score = 0

    sentiment = pipe(element)
    label = sentiment[0]["label"]
    score = sentiment[0]["score"]
    if label in ["LABEL_1", "positive"]:
        total_score += score
    elif label in ["LABEL_0", "negative"]:
        total_score -= score

    total_sentiment = "positive" if total_score > 0 else "negative"

    return total_score, total_sentiment


def extract_words(text: str, min_score: int = 10) -> str:
    """
    Extract important keywords from the given text using Rake.

    Parameters:
    text (str): The text to extract keywords from.
    min_score (int): Minimum score for extracted keywords to be considered (default is 10).

    Returns:
    str: A comma-separated string of extracted keywords.
    """
    all_words = ""
    r.extract_keywords_from_text(text)
    words = r.get_ranked_phrases_with_scores()
    
    for word in words:
        if word[0] > min_score:
            all_words += word[1] + ", "
    return all_words


def make_analysis(keyword: str, min_score: int = 7):
    """
    Perform sentiment and keyword analysis on Reddit posts and news articles related to the given keyword.

    Parameters:
    keyword (str): The keyword to search for.
    min_score (int): Minimum score for extracted keywords to be considered (default is 7).

    Returns:
    dict: A dictionary containing sentiment analysis and important keywords.
    """
    db_details = create_engine_and_sessions(keyword)
    with get_session(db_details["SessionLocal"]) as session:
        all_posts = session.query(RedditPost).all()
        all_news = [news.title for news in session.query(News).all()]
        all_content = [post.title + "\n" + post.content for post in all_posts]
        return {
            "sentiment_text": analyze_sentiment("text", all_content),
            "sentiment_news": analyze_sentiment("news", all_news),
            "important_words": sorted(extract_words(all_content, min_score=min_score), key=lambda x: x[0], reverse=True),
        }


def update_sentiment(db: str):
    """
    Update the sentiment scores and labels for Reddit posts and news articles in the database.

    Parameters:
    db (str): The name of the database.

    Returns:
    None
    """
    db_info = create_engine_and_sessions(db)
    with get_session(db_info["SessionLocal"]) as session:
        posts = session.query(RedditPost).all()
        update_post = []
        update_news = []
        for post in posts:
            combined_text = f"{post.title}\n{post.content}"
            score, label = analyze_sentiment("text", combined_text)
            update_post.append({
                "id": post.id,
                "sentiment_score": score,
                "sentiment_label": label
            })
        session.bulk_update_mappings(RedditPost, update_post)
        session.commit()

        news = session.query(News).all()
        for new in news:
            nscore, nlabel = analyze_sentiment("text", new.title)
            update_news.append({
                "id": new.id,
                "sentiment_score": nscore,
                "sentiment_label": nlabel,
            })
        
        session.bulk_update_mappings(News, update_news)
        session.commit()


def update_words(db: str, min_score: int = 10):
    """
    Update the keywords for Reddit posts in the database.

    Parameters:
    db (str): The name of the database.
    min_score (int): Minimum score for extracted keywords to be considered (default is 10).

    Returns:
    None
    """
    db_info = create_engine_and_sessions(db)
    with get_session(db_info["SessionLocal"]) as session:
        posts = session.query(RedditPost).all()
        update_post = []
        for post in posts:
            combined_text = f"{post.title}\n{post.content}"
            keywords = extract_words(combined_text, min_score=min_score)
            update_post.append({
                "id": post.id,
                "keywords": keywords,
            })
        session.bulk_update_mappings(RedditPost, update_post)
        session.commit()


if __name__ == "__main__":
    stocks_list = ["Ubisoft", "Boeing"]
    for stock in stocks_list:
        update_sentiment(stock)
        update_words(stock, 7)
