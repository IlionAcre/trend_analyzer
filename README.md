# 📊 Marketmood



![Marketmood](https://github.com/user-attachments/assets/bb845ae1-d34e-4509-8b25-053c6f1d6108)



**[Marketmood](https://marketmood.falcontreras.com)** is a dynamic dashboard designed to help users monitor stocks alongside key indicators and sentiment scores derived from Google News and Reddit posts.  
This project provides insightful graphics to visualize relationships between variables, making it a handful tool for market analysis.  

You can check it out at [https://marketmood.falcontreras.com](https://marketmood.falcontreras.com)

---

### 🖥️ Data Sources

The data is constructed from scrapped news from Google News feed, as well as Reddit posts as comments. I used both `rss scraping` and `Playwright` to gather the data.  
All the stock information has been taken from the `yfinance` library, and the indicators were created using `TA-LIB`.  
For the sentiment model, I used a pre-trained model and fine-tuned it using Hugging Face. The training process is fully documented in the notebook.

---

### ✨ Features

- **Stock Monitoring**: Real-time or historical stock data tracking.
- **Sentiment Analysis**: Scores calculated from news articles and Reddit discussions.
- **Visual Insights**: Interactive graphs showcasing correlations between sentiment, stock trends, and indicators.
- **User-Friendly Dashboard**: Built with simplicity and ease of navigation in mind.

---

### 📊 App

- The app was made in Dash, with custom styling using CSS.
- Almost of the graphics are made in Plotly, but the wordclouds were done using the WordCloud library.
- The wordclouds are converted in images then passed to the dashboard.

---

### 🛠️ Deployment

- The data is stored in a multi-tenant postgresql database deployed in Render.
- The application is dockerized and deployed in gcloud.
- A worker in Cloudflare redirects the traffic to the domain.

---

### 🚀 Frameworks and Libraries

#### 🖥️ Web Frameworks
- ![Dash](https://img.shields.io/badge/Dash-0789FA?style=for-the-badge&logo=plotly&logoColor=white)

#### 📊 Data Visualization
- ![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
- ![WordCloud](https://img.shields.io/badge/WordCloud-FF6F00?style=for-the-badge&logo=python&logoColor=white)
- ![Matplotlib](https://img.shields.io/badge/Matplotlib-005571?style=for-the-badge&logo=python&logoColor=white)
- ![Seaborn](https://img.shields.io/badge/Seaborn-3776AB?style=for-the-badge&logo=python&logoColor=white)

#### 📈 Data Processing and Analysis
- ![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
- ![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)

#### 🧑‍💻 Web Scraping
- ![Playwright](https://img.shields.io/badge/Playwright-0078D7?style=for-the-badge&logo=microsoft&logoColor=white)
- ![curl_cffi](https://img.shields.io/badge/curl_cffi-005571?style=for-the-badge&logo=python&logoColor=white)
- ![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-8CAAE6?style=for-the-badge&logo=python&logoColor=white)

#### 📈 Stock Data and Indicators
- ![yfinance](https://img.shields.io/badge/YFinance-000000?style=for-the-badge&logo=python&logoColor=white)
- ![TA-Lib](https://img.shields.io/badge/TA--Lib-0077B5?style=for-the-badge&logo=python&logoColor=white)

#### 🤖 Machine Learning and NLP
- ![Hugging Face](https://img.shields.io/badge/Hugging%20Face-FF6F00?style=for-the-badge&logo=huggingface&logoColor=white)
- ![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

#### 🗄️ Databases and Deployment
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
- ![Render](https://img.shields.io/badge/Render-0093E9?style=for-the-badge&logo=render&logoColor=white)
- ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
- ![Google Cloud](https://img.shields.io/badge/Google%20Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)
- ![Cloudflare](https://img.shields.io/badge/Cloudflare-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)

#### 🧰 Styling
- ![CSS](https://img.shields.io/badge/CSS-1572B6?style=for-the-badge&logo=css3&logoColor=white)
