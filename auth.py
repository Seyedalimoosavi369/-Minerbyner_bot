import json
from urllib.parse import unquote
from functools import wraps
from flask import request, jsonify

def parse_user(init_data):
    if not init_data:
        return None
    try:
        parsed = {}
        for part in init_data.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                parsed[k] = unquote(v)
        user_str = parsed.get("user", "")
        if user_str:
            return json.loads(user_str)
        return None
    except:
        return None

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = parse_user(request.headers.get("X-Init-Data", ""))
        if not user or not user.get("id"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(user, *args, **kwargs)
    return decorated
