# Stock Data Service

# Imports
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask
import threading
import time
import boto3
import yfinance as yf
import logging
import watchtower
import config
import redis

# Create Flask app
app = Flask(__name__)

# Local logging and CloudWatch via watchtower setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("StockDataService")
cw_handler = watchtower.CloudWatchLogHandler(
    log_group=config.CLOUDWATCH_LOG_GROUP,
    stream_name="StockDataService"
)
logger.addHandler(cw_handler)

# Initialize AWS Clients
sqs = boto3.client('sqs', region_name=config.AWS_REGION)
QUEUE_URL = config.SQS_QUEUE_URL

# Initialize Redis client
try:
    redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
    redis_client.ping()
    logger.info("StockDataService connected to Redis successfully")
except Exception as e:
    logger.error("StockDataService error connecting to Redis: %s", e)

def fetch_and_send_stock_data():
    """
    Continuously fetch stock data for tickers found in the Portfolios table.
    Sends the latest stock price data to an SQS queue every 60 seconds and stores the current price in Redis.
    """
    # Initialize DynamoDB resource 
    dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
    portfolio_table = dynamodb.Table(config.PORTFOLIO_TABLE_NAME)
    
    while True:
        try:
            # Scan the portfolio table for tickers
            response = portfolio_table.scan(ProjectionExpression="stock_symbol")
            items = response.get('Items', [])
            
            # Create a set of unique tickers 
            tickers = {item["stock_symbol"] for item in items if "stock_symbol" in item}
            
            if not tickers:
                logger.info("No tickers found in portfolio. Waiting...")
            else:
                for ticker_symbol in tickers:
                    ticker = yf.Ticker(ticker_symbol)
                    data = ticker.history(period="1d")
                    if not data.empty:
                        latest_price = data['Close'].iloc[-1]
                        message_body = f"{ticker_symbol}:{latest_price}"
                        
                        # Send stock data to SQS queue
                        sqs.send_message(
                            QueueUrl=QUEUE_URL,
                            MessageBody=message_body
                        )
                        logger.info("Sent message: %s", message_body)
                        
                        # Store the current price in Redis with key "price:<ticker_symbol>"
                        try:
                            redis_client.set(f"price:{ticker_symbol}", latest_price, ex=300)
                        except Exception as redis_error:
                            logger.error("Error caching current price for %s in Redis: %s", ticker_symbol, redis_error)
                    else:
                        logger.info("No data available for ticker: %s", ticker_symbol)
        except Exception as e:
            logger.error("Error fetching and sending stock data: %s", e)
        
        time.sleep(60)

@app.route('/')
def index():
    """
    Basic health check endpoint to confirm the service is running.
    """
    logger.info("Health check requested for Stock Data Service")
    return "Stock Data Service Running"

if __name__ == '__main__':
    thread = threading.Thread(target=fetch_and_send_stock_data)
    thread.daemon = True
    thread.start()
    app.run(port=5001)