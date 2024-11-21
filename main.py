from dash import Dash, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import graphics
import datetime as dt
from dateutil.relativedelta import relativedelta
from db_manager import create_engine_and_sessions, filter_data_by_date
from sqlalchemy import MetaData, Table, func
from models import RedditPost, News
import matplotlib
import json

matplotlib.use("Agg")

# Load stock data from JSON and set up database connection
with open("stocks_data.json", "r") as f:
    stocks_data = json.load(f)
stock_options = [{"label": stock["name"], "value": stock["nickname"]} for stock in stocks_data]
DEFAULT_KEYWORD = stock_options[0]["value"]
db_info = create_engine_and_sessions(DEFAULT_KEYWORD)
metadata = MetaData()
session = db_info["SessionLocal"]()
stocks_table = Table("stocks", metadata, autoload_with=session.bind)
app = Dash(__name__)

# Define app layout
app.layout = html.Div([
    html.Div([
        html.Div([
            html.H1(id="main_title", className="main_title"),
            dcc.Dropdown(
                id="search_selector",
                options=stock_options,
                placeholder=stock_options[0]["label"],
                searchable=True,
                clearable=False,
            ),
            html.Div([
                dcc.DatePickerRange(
                id="date_picker_stocks",
                min_date_allowed=session.query(func.min(stocks_table.c.Date)).scalar(),
                max_date_allowed=session.query(func.max(stocks_table.c.Date)).scalar(),
                initial_visible_month=dt.datetime.today() - relativedelta(months=6),
                start_date= dt.datetime.today() - relativedelta(months=6),
                end_date = dt.datetime.today()
                ),
            ], className="date_picker_up"),
        ], className="main_bar row bg_dark"),
        html.Div([
            dcc.Loading(
                children=[
                    dcc.Graph(id="stocks_graph", config={"responsive": True}, className="stocks_graph")
                ],
                type="default"
            )
        ], className="stocks_graph_container")
    ], className="container_up bg_dark"),
    
    html.Div([
        html.Div([
            dcc.Loading(
                children=[
                    html.Img(id="wordcloud_news", className="wordcloud", style={"height": "280px", "width": "450px"})
                ],
                type="default"
            )
        ], className="container column words_div bg_dark"),
        html.Div([
            dcc.Loading(children=[
                html.Div(id="sentiment_news"),
                ], 
                type="default"
            ),
            html.Div([
                html.Div([
                    dcc.DatePickerRange(
                        id="date_picker_sentiments",
                        min_date_allowed=session.query(func.min(RedditPost.date)).scalar(),
                        max_date_allowed=session.query(func.max(RedditPost.date)).scalar(),
                        start_date= dt.datetime.today() - relativedelta(months=20),
                        end_date = dt.datetime.today()
                ),], className="date_picker_down container column"),
                dcc.Store(id='toast_trigger'),
                dbc.Toast(
                    id="toast",
                    header="Notification",
                    is_open=False,
                    dismissable=True,
                    duration=4000,
                    children="",
                    class_name="error_message container column"
                ),
                
                dcc.Loading(children=[
                    html.Div(id="indicators", className="container column"),
                    ], 
                    type="default"
                ),
            ], className="container_indicators column"),
            dcc.Loading(children=[
                html.Div(id="sentiment_post"),
                ], 
                type="default"
            ),      
        ], className="container sentiment_box row"),
        html.Div([
            dcc.Loading(
                children=[
                    html.Img(id="wordcloud_post", className="wordcloud", style={"height": "280px", "width": "450px"})
                ],
                type="default"
            )
        ], className="container column words_div bg_dark")
    ], className="container container_down row bg_dark"),
    
    html.Div([
        dcc.Loading(
            children=[
                dcc.Graph(id="chord_plot", className="container column bg_dark", style={"height": "400px", "width": "750px"})
            ],
            type="default"
        ),
        dcc.Loading(
            children=[
                dcc.Graph(id="density_plot", className="container column bg_dark", style={"height": "400px", "width": "750px"})
            ],
            type="default"
        )
    ], className="container container_density row bg_dark"),
    
    html.Div([
        dcc.Loading(
            children=[
                dcc.Graph(id="boxplot_news", className="container column bg_dark", style={"height": "600px", "width": "340px"})
            ],
            type="default"
        ),
        dcc.Loading(
            children=[
                dcc.Graph(id="density_3d_plot", className="container column bg_dark", style={"height": "600px", "width":"800px"})
            ],
            type="default"
        ),
        dcc.Loading(
            children=[
                dcc.Graph(id="boxplot_post", className="container column bg_dark", style={"height": "600px", "width": "340px"})
            ],
            type="default"
        ),
    ], className="container container_density row bg_dark")
    
], className="main_box container column bg_dark")

# Callback to update stock data
@callback(
    Output("main_title", "children"),
    Output("stocks_graph", "figure"),
    Input("search_selector", "value"),
    Input("date_picker_stocks", "start_date"),
    Input("date_picker_stocks", "end_date")
)
def update_stock_data(selected_stock: str, start_date: str, end_date: str) -> tuple:
    """
    Update stock plot based on user input.

    Parameters:
    selected_stock (str): The selected stock.
    start_date (str): The start date for the stock data.
    end_date (str): The end date for the stock data.

    Returns:
    tuple: Updated title and stock figure.
    """
    # Load stock information and set up database connection
    with open("stocks_data.json", "r") as f:
        stocks_data = json.load(f)
        if selected_stock:
            stock_info = next((item for item in stocks_data if item["nickname"] == selected_stock), None)
            db_info = create_engine_and_sessions(selected_stock)
            engine = db_info["engine"]
        else:
            stock_info = stocks_data[0]
            db_info = create_engine_and_sessions(stock_info["nickname"])
            engine = db_info["engine"]

    title = f"{stock_info['name'][:50]} ({stock_info['symbol']}) Exh: {stock_info['exchange']}"
    name = stock_info['nickname']
    
    # Generate the stocks plot
    stocks_figure = graphics.stocks_plot(engine, start_date, end_date, name)

    return title, stocks_figure

# Callback to update sentiment data
@callback(
    Output("wordcloud_news", "src"), 
    Output("wordcloud_post", "src"),
    Output("indicators", "children"),
    Output("sentiment_post", "children"),
    Output("sentiment_news", "children"),
    Output("chord_plot", "figure"),
    Output("density_plot", "figure"),
    Output("boxplot_news", "figure"),
    Output("density_3d_plot", "figure"),
    Output("boxplot_post", "figure"),
    Output('toast_trigger', 'data'),
    Input("search_selector", "value"),
    Input("date_picker_sentiments", "start_date"),
    Input("date_picker_sentiments", "end_date")
)
def update_sentiment_data(selected_stock: str, sentiments_start_date: str, sentiments_end_date: str) -> tuple:
    """
    Update sentiment data, word clouds, and density plots based on user input.

    Parameters:
    selected_stock (str): The selected stock.
    sentiments_start_date (str): The start date for sentiment analysis.
    sentiments_end_date (str): The end date for sentiment analysis.

    Returns:
    tuple: Updated word clouds, sentiment scores, labels, and density plots.
    """
    # Load stock information and set up database connection
    try:
        with open("stocks_data.json", "r") as f:
            stocks_data = json.load(f)
            if selected_stock:
                stock_info = next((item for item in stocks_data if item["nickname"] == selected_stock), None)
                db_info = create_engine_and_sessions(selected_stock)
            else:
                stock_info = stocks_data[0]
                db_info = create_engine_and_sessions(stock_info["nickname"])

        session = db_info["SessionLocal"]()

        # Filter News and RedditPost data by sentiments date range
        filtered_news = filter_data_by_date(session, News, sentiments_start_date, sentiments_end_date)
        filtered_posts = filter_data_by_date(session, RedditPost, sentiments_start_date, sentiments_end_date)
        filtered_stocks = filter_data_by_date(session, stocks_table, sentiments_start_date, sentiments_end_date, date_column="Date")    

        if not filtered_stocks or not filtered_news or not filtered_posts:
            # If no data, return a value to trigger the toast
            raise ValueError("Invalid input for sentiment data.")

        
        good_color = "#81d34d"
        bad_color = "#4a8ca3"
        
        # Get the stocks prices
        start_price = round(filtered_stocks[0].Close, 2)
        end_price = round(filtered_stocks[-1].Close, 2)
        start_color = good_color if start_price >= end_price else bad_color
        end_color = good_color if start_price <= end_price else bad_color

        price_change = round(end_price - start_price, 2)
        percentage_change_row = round(((end_price - start_price) / start_price) * 100, 2)
        percentage_change = f"-{abs(percentage_change_row)}" if percentage_change_row < 0 else f"{percentage_change_row}"

        price_color = good_color if price_change >= 0 else bad_color
        percentage_color = good_color if price_change >= 0 else bad_color
        
        arrow_symbol = "▲" if price_change > 0 else "▼" if price_change < 0 else "─"
        arrow_color = good_color if price_change > 0 else bad_color if price_change < 0 else "white"

        indicators_div = html.Div([
            html.Div(f"Start Price: ${start_price}", style={"color": start_color}),
            html.Div(f"End Price: ${end_price}", style={"color": end_color}),
            html.Div(f"Price Change: ${price_change}", style={"color": price_color}),
            html.Div(f"Percent Change: {percentage_change}%", style={"color": percentage_color}),
            html.Span(arrow_symbol, style={"color": arrow_color, "font-size": "30px"})
        ], className="indicators container column fw_semibold fs_accent")
        
        # Calculate average sentiment score based on filtered data
        sentiment_news = round(sum([entry.sentiment_score for entry in filtered_news]) / len(filtered_news), 2) if filtered_news else 0
        sentiment_post = round(sum([entry.sentiment_score for entry in filtered_posts]) / len(filtered_posts), 2) if filtered_posts else 0
        news_color = good_color if sentiment_news >=0 else bad_color
        post_color = good_color if sentiment_post >=0 else bad_color
        label_news = "Positive" if sentiment_news > 0 else "Negative"
        label_post = "Positive" if sentiment_post > 0 else "Negative"
        
        post_sentiment = html.Div([
            html.Span("Post sentiment:", className="sentiment_title"),
            html.Span(label_post, className="sentiment_title fw_bold", style={"color": post_color}),
            html.Div(
                f"{sentiment_post}",
                className="sentiment_number",
                style={"color": post_color}
                )
        ], className="container column sentiment fs_accent")

        news_sentiment = html.Div([
            html.Span("News sentiment:", className="sentiment_title"),
            html.Span(label_news, className="sentiment_title fw_bold", style={"color": news_color}),
            html.Div(
                f"{sentiment_news}",
                className="sentiment_number",
                style={"color": news_color}
                )
        ], className="container column sentiment fs_accent")
        
        # Generate word clouds based on filtered text data
        news_text = " ".join([entry.title for entry in filtered_news])
        post_text = " ".join([entry.title + " " + entry.content for entry in filtered_posts])
        
        wordcloud_news = f"data:image/png;base64,{graphics.words_plot(news_text)}"
        wordcloud_post = f"data:image/png;base64,{graphics.words_plot(post_text)}"

        # Generate density plots for sentiment scores
        chord_plot = graphics.chord_correlation_plot(filtered_stocks, filtered_news, filtered_posts)
        density_plot = graphics.combined_sentiment_histogram_area_plot(filtered_news, filtered_posts, "News", "Post", "#1f978b", "#39658c")
        
        boxplot_news = graphics.sentiment_boxplot(filtered_news, "News", "#1f978b")
        density_3d_plot = graphics.density_3d_plot(filtered_stocks, filtered_news, filtered_posts)
        boxplot_post = graphics.sentiment_boxplot(filtered_posts, "Post", "#39658c")
        session.close()

        return (
            wordcloud_news,
            wordcloud_post,
            indicators_div,
            post_sentiment,
            news_sentiment,
            chord_plot,
            density_plot,
            boxplot_news,
            density_3d_plot,
            boxplot_post,
            None
        )
    except ValueError as e:
        session.close()
        return (None, None, None, None, None, None, None, None, None, None, f'No data available for the selected date range.\n{e}')

@app.callback(
    Output("toast", "is_open"),
    Output("toast", "children"),
    Input("toast_trigger", "data")
)
def show_toast(message):
    if message:
        return True, message
    return False, ""

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
