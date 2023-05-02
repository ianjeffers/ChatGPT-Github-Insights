import json
import os
import quart
import quart_cors
from quart import request
import httpx
from quart import session
from quart_session import Session
from dotenv import load_dotenv
import uuid

load_dotenv()

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

# Configure session
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret_key_for_demo_purposes")
app.config["SESSION_TYPE"] = "redis"
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
    if properties:
        repo_info = {k: v for k, v in repo_info.items() if k in properties}
    return repo_info

async def get_github_user(access_token):
    url = "https://api.github.com/user"
    user_info = await github_api_request(url, access_token)
    return user_info

@app.get("/repository_info/<string:username>/<string:repo_name>")
async def repository_info(username, repo_name):
    if "access_token" not in session:
        return quart.Response(response='User access token not found', status=401)

    access_token = session["access_token"]
    properties = request.args.get("properties")

    if properties:
        properties = properties.split(",")

    full_repo_name = f"{username}/{repo_name}"
    repo_info = await get_repository_info(full_repo_name, access_token, properties)
    return quart.Response(response=json.dumps(repo_info), status=200)

async def get_repository_file_contents(repo_name, file_path, access_token):
    url = f"https://api.github.com/repos/{repo_name}/contents/{file_path}"
    file_info = await github_api_request(url, access_token)
    return file_info


@app.route("/generate_auth_url")
async def generate_auth_url():
    state = os.urandom(16).hex()
    session["state"] = state
    auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo&redirect_uri=https://{request.headers['Host']}/callback&state={state}"
    return quart.Response(response=json.dumps({"auth_url": auth_url}), status=200)


@app.get("/repository_file_contents/<string:repo_name>/<path:file_path>")
async def repository_file_contents(repo_name, file_path):
    if "access_token" not in session:
        return quart.Response(response='User access token not found', status=401)

    access_token = session["access_token"]
    file_info = await get_repository_file_contents(repo_name, file_path, access_token)
    return quart.Response(response=json.dumps(file_info), status=200)

@app.route("/callback")
async def callback():
    received_state = request.args.get("state")
    if "state" not in session or session["state"] != received_state:
        return quart.Response(response='Invalid state parameter', status=400)

    code = request.args.get("code")
    token_url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": f"https://{request.headers['Host']}/callback",
        "state": session["state"],
    }
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data, headers=headers)

    if response.status_code != 200:
        return quart.Response(response='Failed to get access token', status=400)

    access_token = response.json()["access_token"]

    # Fetch the user's GitHub profile
    user_info = await get_github_user(access_token)
    username = user_info["login"]

    # Store the access token in a secure session
    session["access_token"] = access_token

    return quart.Response(response='OK', status=200)

@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')

@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("./.well-known/ai-plugin.json") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/json")

@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/yaml")

def main():
    app.run(debug=True, host="0.0.0.0", port=5003)

if __name__ == "__main__":
    main()
