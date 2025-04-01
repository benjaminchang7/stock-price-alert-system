# Portfolio Management Service

# Imports
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, jsonify, request
import boto3
import uuid
from boto3.dynamodb.conditions import Attr
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
logger = logging.getLogger("PortfolioManagementService")
cw_handler = watchtower.CloudWatchLogHandler(
    log_group=config.CLOUDWATCH_LOG_GROUP,
    stream_name="PortfolioManagementService"
)
logger.addHandler(cw_handler)

# Initialize AWS Clients
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
portfolio_table = dynamodb.Table(config.PORTFOLIO_TABLE_NAME)

# Initialize Redis client
try:
    redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
    redis_client.ping()
    logger.info("PortfolioManagementService connected to Redis successfully")
except Exception as e:
    logger.error("PortfolioManagementService error connecting to Redis: %s", e)

@app.route('/portfolio', methods=['GET'])
def get_portfolios():
    """
    Retrieve portfolio items. If a user_id is provided as a query parameter,
    filter portfolios by that user. Otherwise, return all portfolios.
    Additionally, fetch the current stock price from Redis for each portfolio item.
    """
    user_id = request.args.get('user_id')
    if user_id:
        response = portfolio_table.scan(
            FilterExpression=Attr('user_id').eq(user_id)
        )
        items = response.get('Items', [])
        logger.info("Retrieved %d portfolios for user_id %s", len(items), user_id)
    else:
        response = portfolio_table.scan()
        items = response.get('Items', [])
        logger.info("Retrieved all %d portfolios", len(items))
    
    # For each portfolio item, fetch the current stock price from Redis
    for item in items:
        if "stock_symbol" in item:
            ticker_symbol = item["stock_symbol"]
            try:
                current_price = redis_client.get(f"price:{ticker_symbol}")
                if current_price is not None:
                    item["current_price"] = current_price.decode('utf-8')
                else:
                    item["current_price"] = "Not Available"
            except Exception as error:
                logger.error("Error fetching current price for %s: %s", ticker_symbol, error)
                item["current_price"] = "Error"
    return jsonify(items)

@app.route('/portfolio', methods=['POST'])
def add_portfolio():
    """
    Add a new portfolio item. Generates a unique portfolio_id and stores the data in DynamoDB.
    """
    data = request.json
    portfolio_id = str(uuid.uuid4())
    data['portfolio_id'] = portfolio_id
    portfolio_table.put_item(Item=data)
    logger.info("Added new portfolio item: %s", data)
    return jsonify({"message": "Portfolio item added", "portfolio": data}), 201

@app.route('/portfolio/<portfolio_id>', methods=['PUT'])
def update_portfolio(portfolio_id):
    """
    Update an existing portfolio item by portfolio_id. Expects a JSON payload with the fields to update.
    """
    data = request.json
    update_expression = "SET "
    expression_attribute_values = {}
    for idx, key in enumerate(data):
        update_expression += f"{key} = :val{idx}, "
        expression_attribute_values[f":val{idx}"] = data[key]
    update_expression = update_expression.rstrip(", ")

    portfolio_table.update_item(
        Key={'portfolio_id': portfolio_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    logger.info("Updated portfolio item %s with data: %s", portfolio_id, data)
    return jsonify({"message": "Portfolio item updated"})

@app.route('/portfolio/<portfolio_id>', methods=['DELETE'])
def delete_portfolio(portfolio_id):
    """
    Delete a portfolio item by portfolio_id.
    """
    portfolio_table.delete_item(Key={'portfolio_id': portfolio_id})
    logger.info("Deleted portfolio item with portfolio_id: %s", portfolio_id)
    return jsonify({"message": "Portfolio item deleted"})

@app.route('/')
def index():
    """
    Basic health check endpoint.
    """
    logger.info("Health check requested for Portfolio Management Service")
    return "Portfolio Management Service Running"

if __name__ == '__main__':
    app.run(port=5003)