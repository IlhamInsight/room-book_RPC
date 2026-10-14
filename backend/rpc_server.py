"""
Standalone Flask JSON-RPC 2.0 Server.
Used for Distributed Systems (Sistem Terdistribusi) architecture.
Run independently with:
    cd backend
    python rpc_server.py
Accessible at: http://localhost:5000/api/rpc/
"""
import os
import sys

# Ensure backend root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Initialize Django ORM environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from core.api.rpc_dispatcher import rpc_dispatcher

app = Flask(__name__)
# Enable CORS for all routes so frontend (Vite/React) on any port or domain can connect
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "Room Booking JSON-RPC 2.0 Service",
        "protocol": "JSON-RPC 2.0",
        "status": "online",
        "rpc_endpoint": "/api/rpc/",
        "methods": list(rpc_dispatcher.registry.keys())
    })

@app.route('/api/rpc/', methods=['POST', 'OPTIONS'])
def json_rpc_handler():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    raw_body = request.get_data()
    meta = {
        'HTTP_AUTHORIZATION': request.headers.get('Authorization', '')
    }

    result = rpc_dispatcher.dispatch(raw_body=raw_body, request_meta=meta)
    return jsonify(result), 200

@app.route('/media/<path:filename>', methods=['GET'])
def serve_media(filename):
    media_dir = os.path.join(current_dir, 'media')
    return send_from_directory(media_dir, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"=====================================================")
    print(f"[START] Starting Flask JSON-RPC 2.0 Server on port {port}")
    print(f"[ENDPOINT] http://localhost:{port}/api/rpc/")
    print(f"[METHODS] Registered Procedures: {len(rpc_dispatcher.registry)}")
    print(f"=====================================================")
    app.run(host='0.0.0.0', port=port, debug=True)
