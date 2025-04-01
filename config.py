# config.py
AWS_REGION = "us-east-1"
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/762233738088/StockPriceQueue"
ALERT_TABLE_NAME = "AlertConditions"
PORTFOLIO_TABLE_NAME = "Portfolios"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
CLOUDWATCH_LOG_GROUP = "StockPriceAlert"