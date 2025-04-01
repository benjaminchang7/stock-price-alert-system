# WebUI Service

# Imports
from flask import Flask, render_template, request, jsonify
import requests
from flask_cors import CORS

# Create Flask app
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """
    Simple health check endpoint
    """
    return render_template('index.html')

@app.route('/api/portfolio', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_portfolio():
    """
    Proxy endpoint: Portfolio Management Service
    """
    url = "http://localhost:5003/portfolio"
    if request.method == 'GET':
        resp = requests.get(url, params=request.args)
        return (resp.content, resp.status_code, resp.headers.items())
    elif request.method == 'POST':
        resp = requests.post(url, json=request.get_json())
        return (resp.content, resp.status_code, resp.headers.items())
    elif request.method == 'PUT':
        portfolio_id = request.args.get('portfolio_id')
        if not portfolio_id:
            return jsonify({"error": "portfolio_id is required"}), 400
        full_url = f"{url}/{portfolio_id}"
        resp = requests.put(full_url, json=request.get_json())
        return (resp.content, resp.status_code, resp.headers.items())
    elif request.method == 'DELETE':
        portfolio_id = request.args.get('portfolio_id')
        if not portfolio_id:
            return jsonify({"error": "portfolio_id is required"}), 400
        full_url = f"{url}/{portfolio_id}"
        resp = requests.delete(full_url)
        return (resp.content, resp.status_code, resp.headers.items())

@app.route('/api/alerts')
def proxy_alerts():
    """
    Proxy endpoint: triggered alerts
    """
    try:
        resp = requests.get("http://localhost:5002/alerts")
        return (resp.content, resp.status_code, resp.headers.items())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alert', methods=['GET', 'POST', 'DELETE'])
def proxy_alert():
    """
    Proxy endpoint: Alert Conditions (list, create, delete)
    """
    url = "http://localhost:5002/alert"
    if request.method == 'GET':
        resp = requests.get(url)
        return (resp.content, resp.status_code, resp.headers.items())
    elif request.method == 'POST':
        resp = requests.post(url, json=request.get_json())
        return (resp.content, resp.status_code, resp.headers.items())
    elif request.method == 'DELETE':
        alert_id = request.args.get('alert_id')
        if not alert_id:
            return jsonify({"error": "alert_id is required"}), 400
        full_url = f"{url}?alert_id={alert_id}"
        resp = requests.delete(full_url)
        return (resp.content, resp.status_code, resp.headers.items())

if __name__ == '__main__':
    app.run(port=8000, debug=True)