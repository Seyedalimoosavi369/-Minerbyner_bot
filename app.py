import os
from flask import Flask, jsonify
from flask_cors import CORS
from db import init_db
from routes.user import user_bp
from routes.shop import shop_bp
from routes.network import network_bp
from routes.wallet import wallet_bp
from routes.admin import admin_bp

app = Flask(__name__)
CORS(app, origins="*")

app.register_blueprint(user_bp)
app.register_blueprint(shop_bp)
app.register_blueprint(network_bp)
app.register_blueprint(wallet_bp)
app.register_blueprint(admin_bp)

@app.route("/")
def index():
    return jsonify({"status": "Minerbyner API running"})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
