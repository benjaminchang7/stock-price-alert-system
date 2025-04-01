# Alert Management Service

# Imports 
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, jsonify, request
import boto3
import redis
import threading
import time
import json
from boto3.dynamodb.conditions import Attr
import logging
import watchtower
import config

# Create Flask app
app = Flask(__name__)

# Local logging and CloudWatch via watchtower setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("AlertManagementService")
cw_handler = watchtower.CloudWatchLogHandler(
    log_group=config.CLOUDWATCH_LOG_GROUP,
    stream_name="AlertManagementService"
)
logger.addHandler(cw_handler)

# Initialize AWS Clients
sqs = boto3.client('sqs', region_name=config.AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
alert_table = dynamodb.Table(config.ALERT_TABLE_NAME)
QUEUE_URL = config.SQS_QUEUE_URL

# Initialize Redis client
try:
    redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
    redis_client.ping()
    logger.info("Connected to Redis successfully")
except Exception as e:
    logger.error("Error connecting to Redis: %s", e)

def process_stock_data():
    """
    Continuously poll stock price updates from SQS and check for triggered alerts.
    """
    while True:
        try:
            # Poll for messages from SQS
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20
            )
            messages = response.get('Messages', [])

            for msg in messages:
                body = msg['Body']
                try:
                    # Expected format: "AAPL:150.0"
                    symbol, price = body.split(":") 
                    price = float(price)
                except Exception as parse_error:
                    logger.error("Error parsing message: %s", parse_error)
                    continue

                # Scan the AlertConditions table for active alerts
                conditions = alert_table.scan(
                    FilterExpression=Attr('stock_symbol').eq(symbol)
                ).get('Items', [])

                for condition in conditions:
                    condition_type = condition.get('condition_type')
                    threshold = float(condition.get('threshold'))
                    alert_id = condition.get('alert_id')
                    trigger = False
                    
                    if condition_type == 'above' and price > threshold:
                        trigger = True
                    elif condition_type == 'below' and price < threshold:
                        trigger = True

                    if trigger:
                        alert_data = {
                            'alert_id': alert_id,
                            'stock_symbol': symbol,
                            'price': price,
                            'condition': condition_type,
                            'threshold': threshold
                        }
                        # Cache the alert in Redis for 5 minutes
                        try:
                            redis_client.set(f"alert:{alert_id}", json.dumps(alert_data), ex=300)
                        except Exception as redis_error:
                            logger.error("Error caching alert in Redis: %s", redis_error)
                        logger.info("Triggered alert: %s", alert_data)

                # Delete processed message from SQS
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=msg['ReceiptHandle']
                )

        except Exception as e:
            logger.error("Error processing stock data: %s", e)

        time.sleep(1)

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Get all active alerts from Redis.
    """
    try:
        keys = redis_client.keys("alert:*")
        alerts = []
        for key in keys:
            data = redis_client.get(key)
            if data:
                alerts.append(json.loads(data))
        logger.info("Retrieved %d alerts", len(alerts))
        return jsonify(alerts)
    except Exception as e:
        logger.error("Error retrieving alerts: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/alert', methods=['GET', 'POST', 'DELETE'])
def manage_alert():
    """
    Handle CRUD operations for alert conditions.
    """
    if request.method == 'GET':
        response = alert_table.scan()
        items = response.get('Items', [])
        logger.info("Retrieved %d alert conditions", len(items))
        return jsonify(items)
    elif request.method == 'POST':
        data = request.json
        alert_table.put_item(Item=data)
        logger.info("Created alert condition: %s", data)
        return jsonify({"message": "Alert condition created", "alert": data}), 201
    elif request.method == 'DELETE':
        alert_id = request.args.get('alert_id')
        if not alert_id:
            logger.error("DELETE /alert called without alert_id")
            return jsonify({"error": "alert_id is required"}), 400
        alert_table.delete_item(Key={'alert_id': alert_id})
        logger.info("Deleted alert condition with alert_id: %s", alert_id)
        return jsonify({"message": "Alert condition deleted"})

@app.route('/')
def index():
    """
    Simple health check endpoint.
    """
    logger.info("Health check requested")
    return "Alert Management Service Running"

if __name__ == '__main__':
    thread = threading.Thread(target=process_stock_data)
    thread.daemon = True
    thread.start()
    app.run(port=5002)