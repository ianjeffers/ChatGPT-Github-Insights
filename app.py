import os
import quart
import aioredis
import quart_cors
from dotenv import load_dotenv
from quart_session import Session
from routes import routes
from github_auth_routes import auth_routes

load_dotenv()

app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret_key_for_demo_purposes")
app.config["SESSION_TYPE"] = "redis"

redis = aioredis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
Session(app)

app.register_blueprint(routes)
app.register_blueprint(auth_routes)

@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')

@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    with open("./.well-known/ai-plugin.json") as f:
        return quart.Response(f.read(), mimetype="text/json")

@app.get("/openapi.yaml")
async def openapi_spec():
    with open("openapi.yaml") as f:
        return quart.Response(f.read(), mimetype="text/yaml")

def main():
    app.run(debug=True, host="0.0.0.0", port=5003)

if __name__ == "__main__":
    main()
