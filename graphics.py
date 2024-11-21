import base64
import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
from plotly.subplots import make_subplots
from scipy.stats import gaussian_kde
from sqlalchemy import text
from wordcloud import STOPWORDS, WordCloud
import talib as ta

matplotlib.use('TkAgg')

custom_stopwords = set(STOPWORDS)
custom_stopwords.update(["anything", "anyone"])
pio.renderers.default = "browser"

def stocks_plot(engine, date_start: str, date_end: str, name:str) -> go.Figure:
    """
    Generate a stock price plot with indicators such as SMA, Bollinger Bands, and MACD.

    Parameters:
    engine: SQLAlchemy engine to connect to the database.
    date_start (str): The start date for the stock data.
    date_end (str): The end date for the stock data.
    name (str): Name of the stock.

    Returns:
    plotly.graph_objs.Figure: The generated stock price figure.
    """
    query = """
        SELECT "Date", "Open", "High", "Low", "Close", "Volume"
        FROM stocks
    """

    # Fetch stock data from the database
    with engine.connect() as conn:
        df = pd.read_sql_query(text(query), conn)
    
    # Process data for plotting
    df["Date"] = pd.to_datetime(df["Date"], utc=True)
    df.set_index("Date", inplace=True)
    df["SMA"] = ta.SMA(df["Close"], timeperiod=20)  # Simple Moving Average
    df["BB_High"], df["BB_Mid"], df["BB_Low"] = ta.BBANDS(df["Close"], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)  # Bollinger Bands

    # Calculate MACD
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = ta.MACD(df["Close"], fastperiod=12, slowperiod=26, signalperiod=9)

    # Filter data for the specified date range
    df = df[(df.index >= date_start) & (df.index <= date_end)]

    # Create subplots for the stock data and MACD
    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.2,
        row_heights=[0.7, 0.3],
        subplot_titles=[f"{name} indicators"]
    )

    # Add candlestick chart for stock prices
    candlestick = go.Candlestick(
        x=df.index,
        open=df.Open,
        high=df.High,
        low=df.Low,
        close=df.Close,
        increasing_line_color= "#27ad81", decreasing_line_color= "#2c728e",
        name="Price"
    )
    fig.add_trace(candlestick, row=1, col=1)
    candlestick.hoverlabel = dict(font_size=16, font_family="Open Sans", bgcolor="black", font_color="white")

    # Add SMA and Bollinger Bands
    fig.add_trace(go.Scatter(x=df.index, y=df.SMA, line={"color": "blue", "width": 2}, name="SMA"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.BB_High, line={"color": "red", "width": 1}, name="Upper BB"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.BB_Mid, line={"color": "red", "width": 1}, name="Middle BB"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.BB_Low, line={"color": "green", "width": 1}, name="Lower BB"), row=1, col=1)

    # Add MACD indicator
    fig.add_trace(go.Scatter(x=df.index, y=df.MACD, line={"color": "yellow", "width": 2}, name="MACD"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.MACD_Signal, line={"color": "purple", "width": 2}, name="MACD Signal"), row=2, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df.MACD_Hist, name="MACD Delta", marker_color='gray'), row=2, col=1)

    # Update layout for aesthetics
    fig.update_layout(
        yaxis_title="Price",
        xaxis_title="Date",
        xaxis_title_font=dict(size=16),
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(t=60),
        hoverlabel=dict(
            bgcolor="black",
            font_size=12,
            font_family="Arial",
            font_color="white"
        )
    )
    fig.update_yaxes(title_text="MACD Value", row=2, col=1)

    return fig

def words_plot(data: str) -> str:
    """
    Generate a word cloud from the given text data.

    Parameters:
    data (str): Text data to generate the word cloud from.

    Returns:
    str: Base64 encoded image of the generated word cloud.
    """
    font_path = "fonts/ARIAL.ttf"
    wordcloud = WordCloud(
        stopwords=custom_stopwords,
        background_color="black",
        font_path=font_path,
        width=600,
        height=400,
        max_words=50,
    ).generate(data)

    # Convert word cloud image to base64 string
    img_buffer = io.BytesIO()
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.savefig(img_buffer, format="png", bbox_inches='tight', pad_inches=0)
    plt.close()
    img_buffer.seek(0)
    img_formatted = base64.b64encode(img_buffer.read()).decode("utf-8")
    
    return img_formatted

def sentiment_boxplot(query_result, title: str, color: str) -> go.Figure:
    """
    Plots a boxplot for sentiment scores from the given query result.

    Parameters:
    query_result (list): The SQLAlchemy query result containing date and sentiment_score.
    title (str): The title of the boxplot.
    color (str): Color to be used for the boxplot.

    Returns:
    plotly.graph_objs._figure.Figure: The generated boxplot figure.
    """
    df = pd.DataFrame([{
        'date': row.date,
        'sentiment_score': row.sentiment_score
    } for row in query_result])

    df = df[(df["sentiment_score"] < -0.5) | (df["sentiment_score"] > 0.5)]

    fig = go.Figure()
    fig.add_trace(go.Box(
        y=df['sentiment_score'],
        name=title,
        marker_color=color,
        boxmean='sd',
        hovertemplate="Sentiment: %{y:.2f}"
    ))

    fig.update_layout(
        yaxis_title="Sentiment Score",
        template="plotly_dark",
        showlegend=False,
        hoverlabel=dict(
            bgcolor="black",
            font_size=12,
            font_family="Open Sans",
            font_color="white"
        ),
        title=f"{title} score"
    )

    return fig

def combined_sentiment_histogram_area_plot(news_result, post_result, news_title: str, post_title: str, news_color: str, post_color: str) -> px.histogram:
    """
    Plots an interactive density line plot for sentiment scores from news and post query results.

    Parameters:
    news_result (list): The SQLAlchemy query result for news containing date and sentiment_score.
    post_result (list): The SQLAlchemy query result for posts containing date and sentiment_score.
    news_title (str): The title of the density plot for news.
    post_title (str): The title of the density plot for posts.
    news_color (str): Color to be used for the news density line.
    post_color (str): Color to be used for the post density line.

    Returns:
    plotly.graph_objs._figure.Figure: The generated density line plot figure.
    """
    
    news_scores = [row.sentiment_score for row in news_result]
    post_scores = [row.sentiment_score for row in post_result]

    news_kde = gaussian_kde(news_scores)
    news_x = np.linspace(min(news_scores), max(news_scores), 500)
    news_y = news_kde(news_x)

    post_kde = gaussian_kde(post_scores)
    post_x = np.linspace(min(post_scores), max(post_scores), 500)
    post_y = post_kde(post_x)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=news_x,
        y=news_y,
        mode='lines',
        name=news_title,
        line=dict(color=news_color, width=2),
        fill='tozeroy',
        opacity=0.5,
        hovertemplate="Sentiment: %{x:.2f}<br>Density: %{y:.2f}"


    ))

    fig.add_trace(go.Scatter(
        x=post_x,
        y=post_y,
        mode='lines',
        name=post_title,
        line=dict(color=post_color, width=2),
        fill='tozeroy',
        opacity=0.5,
        hovertemplate="Sentiment: %{x:.2f}<br>Density: %{y:.2f}"

    ))

    fig.update_layout(
        title="Sentiment Score Density Comparison",
        xaxis_title="Sentiment Score",
        yaxis_title="Density",
        template="plotly_dark",
        showlegend=True,
        hoverlabel=dict(
            bgcolor="black",
            font_size=12,
            font_family="Open Sans",
            font_color="white"
        )
    )

    return fig

def density_3d_plot(filtered_stocks, filtered_news, filtered_posts) -> go.Figure:
    """
    Creates a 3D surface plot showing the relationship between stock price change percentage and sentiment scores (both news and posts).

    Parameters:
    filtered_stocks (list): The SQLAlchemy query result containing stock data with 'Date' and 'Close' columns.
    filtered_news (list): The SQLAlchemy query result containing news sentiment scores.
    filtered_posts (list): The SQLAlchemy query result containing post sentiment scores.

    Returns:
    plotly.graph_objs._figure.Figure: The generated 3D surface plot.
    """
    # Convert filtered query results to DataFrames
    stock_df = pd.DataFrame([{
        'date': row.Date,
        'close': row.Close
    } for row in filtered_stocks]).drop_duplicates()

    news_df = pd.DataFrame([{
        'date': row.date,
        'sentiment_score': row.sentiment_score
    } for row in filtered_news]).drop_duplicates()

    posts_df = pd.DataFrame([{
        'date': row.date,
        'sentiment_score': row.sentiment_score
    } for row in filtered_posts]).drop_duplicates()

    # Convert dates to datetime and normalize to remove time component
    stock_df['date'] = pd.to_datetime(stock_df['date']).dt.tz_localize(None).dt.normalize()
    news_df['date'] = pd.to_datetime(news_df['date']).dt.tz_localize(None).dt.normalize()
    posts_df['date'] = pd.to_datetime(posts_df['date']).dt.tz_localize(None).dt.normalize()

    # Remove duplicates and set date as index for stock data
    stock_df = stock_df.drop_duplicates(subset='date')
    news_df = news_df.drop_duplicates(subset='date')
    posts_df = posts_df.drop_duplicates(subset='date')

    stock_df.set_index('date', inplace=True)
    stock_df = stock_df.asfreq('D').ffill()

    # Calculate daily percentage change in stock price
    stock_df['price_change'] = stock_df['close'].pct_change() * 100
    stock_df.dropna(subset=['price_change'], inplace=True)

    # Merge stock and sentiment data on the date
    merged_data = pd.merge(stock_df.reset_index(), news_df, on='date', how='inner')
    merged_data = pd.merge(merged_data, posts_df, on='date', how='inner').dropna()

    # Prepare data for 3D plot
    x = merged_data['sentiment_score_x']  # News sentiment score
    y = merged_data['sentiment_score_y']  # Posts sentiment score
    z = merged_data['price_change']       # Price change percentage

    # Create a regular grid for 3D plotting
    x_linspace = np.linspace(x.min(), x.max(), 50)
    y_linspace = np.linspace(y.min(), y.max(), 50)
    x_grid, y_grid = np.meshgrid(x_linspace, y_linspace)

    # Interpolate z values on the grid
    from scipy.interpolate import griddata
    z_grid = griddata((x, y), z, (x_grid, y_grid), method='cubic')

    # Create 3D surface plot
    fig = go.Figure(data=[go.Surface(
        x=x_grid,
        y=y_grid,
        z=z_grid,
        colorscale='Viridis',
        hovertemplate="News Score: %{x:.2f}<br>Post Score: %{y:.2f}<br>Price Change: %{z:.2f}%"
    )])

    # Update layout for better visual aesthetics
    fig.update_layout(
        title='Specific Sentiment vs Stock Price Change',
        scene=dict(
            xaxis_title='News',
            yaxis_title='Posts',
            zaxis_title='Price Change (%)',
            camera=dict(
                center=dict(x=0, y=0, z=-0.28),
            )
        ),
        template='plotly_dark',
        margin=dict(l=0, r=0, t=100, b=20),
        hoverlabel=dict(
            bgcolor='black',
            font_size=12,
            font_family="Open Sans",
            font_color='white'
        )
    )

    return fig

def chord_correlation_plot(filtered_stocks, filtered_news, filtered_posts) -> go.Figure:
    """
    Creates a chord diagram showing the relationship between sentiment categories (positive, negative, neutral) from both news and posts, and stock price change (increase, decrease, stable).

    Parameters:
    filtered_stocks (list): The SQLAlchemy query result containing stock data with 'Date' and 'Close' columns.
    filtered_news (list): The SQLAlchemy query result containing news sentiment scores.
    filtered_posts (list): The SQLAlchemy query result containing post sentiment scores.

    Returns:
    plotly.graph_objs._figure.Figure: The generated chord diagram plot.
    """
    # Convert filtered query results to DataFrames
    stock_df = pd.DataFrame([{
        'date': row.Date,
        'close': row.Close
    } for row in filtered_stocks]).drop_duplicates()

    news_df = pd.DataFrame([{
        'date': row.date,
        'sentiment_score': row.sentiment_score
    } for row in filtered_news]).drop_duplicates()

    posts_df = pd.DataFrame([{
        'date': row.date,
        'sentiment_score': row.sentiment_score
    } for row in filtered_posts]).drop_duplicates()

    # Convert dates to datetime and normalize to remove time component
    stock_df['date'] = pd.to_datetime(stock_df['date']).dt.tz_localize(None).dt.normalize()
    news_df['date'] = pd.to_datetime(news_df['date']).dt.tz_localize(None).dt.normalize()
    posts_df['date'] = pd.to_datetime(posts_df['date']).dt.tz_localize(None).dt.normalize()

    stock_df = stock_df.drop_duplicates(subset='date')
    news_df = news_df.drop_duplicates(subset='date')
    posts_df = posts_df.drop_duplicates(subset='date')

    stock_df.set_index('date', inplace=True)
    stock_df = stock_df.asfreq('D').ffill()

    # Calculate daily percentage change in stock price
    stock_df['price_change'] = stock_df['close'].pct_change() * 100

    # Categorize price changes
    conditions = [
        (stock_df['price_change'] > 0),
        (stock_df['price_change'] < 0),
        (stock_df['price_change'] == 0)
    ]
    categories = ['Increase', 'Decrease', 'Stable']
    stock_df['price_category'] = np.select(conditions, categories, default='Stable')

    # Categorize sentiment scores for news and posts
    sentiment_conditions_news = [
        (news_df['sentiment_score'] > 0),
        (news_df['sentiment_score'] < 0),
        (news_df['sentiment_score'] == 0)
    ]
    sentiment_categories_news = ['News Positive', 'News Negative', 'News Neutral']
    news_df['sentiment_category'] = np.select(sentiment_conditions_news, sentiment_categories_news, default='News Neutral')

    sentiment_conditions_posts = [
        (posts_df['sentiment_score'] > 0),
        (posts_df['sentiment_score'] < 0),
        (posts_df['sentiment_score'] == 0)
    ]
    sentiment_categories_posts = ['Posts Positive', 'Posts Negative', 'Posts Neutral']
    posts_df['sentiment_category'] = np.select(sentiment_conditions_posts, sentiment_categories_posts, default='Posts Neutral')

    combined_news = pd.merge(stock_df.reset_index(), news_df, on='date', how='inner')
    combined_posts = pd.merge(stock_df.reset_index(), posts_df, on='date', how='inner')
    combined_df = pd.concat([combined_news, combined_posts], axis=0)

    # Relationship count between sentiment and price categories
    combined_df = combined_df[['sentiment_category', 'price_category']]
    relationship_counts = combined_df.groupby(['sentiment_category', 'price_category']).size().unstack(fill_value=0)

    relationship_counts_percent = relationship_counts.apply(lambda x: (x / x.sum()) * 100, axis=1)

    all_sentiment_categories = sentiment_categories_news + sentiment_categories_posts
    labels = all_sentiment_categories + categories

    source = []
    target = []
    value = []

    for i, sentiment in enumerate(all_sentiment_categories):
        for j, price in enumerate(categories):
            if sentiment in relationship_counts_percent.index and price in relationship_counts_percent.columns:
                source.append(i)
                target.append(len(all_sentiment_categories) + j)
                value.append(relationship_counts_percent.loc[sentiment, price])

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=labels,
            color=['#1b8c73', '#482777', '#3b528b', '#5ec962', '#423980', '#fde725', '#21918c', '#440154', '#fde725']

        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=[
                # News Positive
                'rgba(26, 178, 166, 0.4)', # Green (brighter shade)             
                'rgba(100, 45, 135, 0.6)',   # Purple (base link)
                'rgba(255, 235, 59, 0.4)',  # Yellow (brighter shade)

                # News Negative
                'rgba(42, 160, 155, 0.4)',  # Green (lighter shade)
                'rgba(100, 45, 135, 0.4)',  # Purple (lighter shade)
                'rgba(255, 251, 123, 0.4)', # Yellow (lighter shade)

                # Posts Positive
                'rgba(20, 120, 110, 0.4)',  # Green (darker shade)
                'rgba(100, 45, 135, 0.6)',  # Purple (darker shade)
                'rgba(220, 195, 20, 0.4)',  # Yellow (darker shade)

                # Posts Negative
                'rgba(48, 145, 125, 0.4)',  # Green (more saturated shade)
                'rgba(100, 45, 135, 0.4)',  # Purple (more saturated shade)
                'rgba(245, 225, 70, 0.4)'   # Yellow (more saturated shade)
            ],
            hovertemplate="Sentiment: %{source.label}<br>Price Change: %{target.label}<br>Percentage: %{value:.2f}%"
        )
    )])

    fig.update_layout(
        title_text='General Sentiment vs Stock Price Change',
        font_size=12,
        template='plotly_dark',
        margin=dict(t=100),
        hoverlabel=dict(
            bgcolor='black',
            font_size=12,
            font_family="Open Sans",
            font_color='white'
        )
    )

    return fig
