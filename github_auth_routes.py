import json
import os
import quart
import httpx
from quart import request
from dotenv import load_dotenv
from access_token_checker import AccessTokenChecker

auth_routes = quart.Blueprint("auth_routes", __name__)

load_dotenv()

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
CALLBACK = "/callback"
CALLBACK_PATH = "https://b96f-2600-1700-7c00-6df0-3c77-1c82-d8f5-b916.ngrok-free.app" + CALLBACK

access_token_checker = AccessTokenChecker()

@auth_routes.route("/generate_auth_url")
async def generate_auth_url():
    state = os.urandom(16).hex()
    await access_token_checker.set_state(state)
    auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo&redirect_uri={CALLBACK_PATH}&state={state}"
    return quart.Response(response=json.dumps({"auth_url": auth_url}), status=200)

@auth_routes.route("/callback")
async def callback():
    received_state = request.args.get("state")
    session_state = await access_token_checker.get_state()
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
    await access_token_checker.set_access_token(access_token)
    return quart.Response(response='OK', status=200)

