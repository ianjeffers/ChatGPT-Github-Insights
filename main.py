import json
import os
import uuid
import quart
import httpx
import aioredis
import quart_cors
from quart import request
from dotenv import load_dotenv
from quart_session import Session

load_dotenv()

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
CALLBACK_PATH = "https://b2d0-2600-1700-7c00-6df0-3921-cadb-59a-c723.ngrok-free.app/callback"

app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret_key_for_demo_purposes")
app.config["SESSION_TYPE"] = "redis"

redis = aioredis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
Session(app)

async def github_api_request(url, access_token):
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    return response.json()

async def get_repository_info(repo_name, access_token, properties=None):
    url = f"https://api.github.com/repos/{repo_name}"
    repo_info = await github_api_request(url, access_token)
    return {k: v for k, v in repo_info.items() if k in properties} if properties else repo_info

@app.get("/repository_info/<string:username>/<string:repo_name>")
async def repository_info(username, repo_name):
    access_token = await redis.get("access_token")
    if access_token is None:
        return quart.Response(response='User access token not found', status=401)
    properties = request.args.get("properties", "").split(",")
    repo_info = await get_repository_info(f"{username}/{repo_name}", access_token, properties)
    return quart.Response(response=json.dumps(repo_info), status=200)

async def list_repository_directory(username, repo_name, file_path, access_token):
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    return await github_api_request(url, access_token)

async def list_repository_directory_endpoint(username, repo_name, file_path=""):
    access_token = await redis.get("access_token")
    if access_token is None:
        return quart.Response(response='User access token not found', status=401)
    directory_contents = await list_repository_directory(username, repo_name, file_path, access_token)
    return quart.Response(response=json.dumps(directory_contents), status=200)

@app.get("/list_repository_directory/<string:username>/<string:repo_name>")
@app.get("/list_repository_directory/<string:username>/<string:repo_name>/<string:file_path>")
async def list_repository_directory_route(username, repo_name, file_path=""):
    return await list_repository_directory_endpoint(username, repo_name, file_path)

async def get_repository_file_contents(username, repo_name, file_path, access_token):
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    return await github_api_request(url, access_token)

@app.get("/repository_file_contents/<string:username>/<string:repo_name>/<path:file_path>")
async def repository_file_contents(username, repo_name, file_path):
    access_token = await redis.get("access_token")
    if access_token is None:
        return quart.Response(response='User access token not found', status=401)
    file_info = await get_repository_file_contents(username, repo_name, file_path, access_token)
    return quart.Response(response=json.dumps(file_info), status=200)

@app.route("/generate_auth_url")
async def generate_auth_url():
    state = os.urandom(16).hex()
    await redis.set("state", state)
    auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo&redirect_uri={CALLBACK_PATH}&state={state}"
    return quart.Response(response=json.dumps({"auth_url": auth_url}), status=200)

@app.route("/callback")
async def callback():
    received_state = request.args.get("state")
    session_state = await redis.get("state")
    if session_state != received_state:
        return quart.Response(response='Invalid state parameter', status=400)

    code = request.args.get("code")
    token_url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_PATH,
        "state": session_state,
    }
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data, headers=headers)

    if response.status_code != 200:
        return quart.Response(response='Failed to get access token', status=400)

    access_token = response.json()["access_token"]
    await redis.set("access_token", access_token)
    return quart.Response(response='OK', status=200)

async def get_github_user(access_token):
    url = "https://api.github.com/user"
    return await github_api_request(url, access_token)

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
