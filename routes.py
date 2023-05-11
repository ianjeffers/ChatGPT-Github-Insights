import json
import quart
from quart import Blueprint, request
from access_token_checker import AccessTokenChecker
from github_api import GitHubAPI

routes = Blueprint("routes", __name__)
access_token_checker = AccessTokenChecker()

@routes.get("/repository_info/<string:username>/<string:repo_name>")
async def repository_info(username, repo_name):
    try:
        access_token = await access_token_checker.check_access_token()
    except ValueError as e:
        return quart.Response(response=str(e), status=401)
    github_api = GitHubAPI(access_token)
    repo_str = f"{username}/{repo_name}"
    repo_info = await github_api.get_repository_info(repo_str)
    print(repo_info, repo_str)
    return quart.Response(response=json.dumps(repo_info), status=200)

@routes.get("/list_repository_directory/<string:username>/<string:repo_name>")
@routes.get("/list_repository_directory/<string:username>/<string:repo_name>/<path:file_path>")
async def list_repository_directory_route(username, repo_name, file_path=""):
    try:
        access_token = await access_token_checker.check_access_token()
    except ValueError as e:
        return quart.Response(response=str(e), status=401)
    github_api = GitHubAPI(access_token)
    directory_contents = await github_api.list_repository_directory(username, repo_name, file_path)
    return quart.Response(response=json.dumps(directory_contents), status=200)

@routes.get("/repository_file_contents/<string:username>/<string:repo_name>/<path:file_path>")
async def repository_file_contents(username, repo_name, file_path):
    try:
        access_token = await access_token_checker.check_access_token()
    except ValueError as e:
        return quart.Response(response=str(e), status=401)
    github_api = GitHubAPI(access_token)
    file_info = await github_api.get_repository_file_contents(username, repo_name, file_path)
    file_contents = file_info.get("content", "")

    code_entities = []
    if file_path.endswith('.py'):
        code_entities += get_classes_from_py_code(file_contents)
        code_entities += get_functions_from_py_code(file_contents)
        
    elif file_path.endswith('.js'):
        code_entities += get_classes_from_js_code(file_contents)
        code_entities += get_functions_from_js_code(file_contents)

    for code, info in code_entities:
        code_id = f"{username}/{repo_name}/{file_path}/{info['name']}"
        code_embedding = get_code_embedding(code)
        store_code_embeddings_in_pinecone(code_id, code_embedding)
    
    return quart.Response(response=json.dumps(file_info), status=200)


@routes.post("/create_issue/<string:username>/<string:repo_name>")
async def create_issue_route(username, repo_name):
    try:
        access_token = await access_token_checker.check_access_token()
    except ValueError as e:
        return quart.Response(response=str(e), status=401)
    github_api = GitHubAPI(access_token)
    data = await request.get_json()
    title = data.get("title")
    body = data.get("body")
    full_path = f"{username}/{repo_name}"
    issue_info = await github_api.create_issue(full_path, title, body)
    return quart.Response(response=json.dumps(issue_info), status=200)

@routes.get("/search_code")
async def search_code_route():
    try:
        access_token = await access_token_checker.check_access_token()
    except ValueError as e:
        return quart.Response(response=str(e), status=401)
    github_api = GitHubAPI(access_token)
    query = request.args.get("query")
    repo_name = request.args.get("repo_name")
    search_results = await github_api.search_code(query, repo_name)
    return quart.Response(response=json.dumps(search_results), status=200)

@routes.get("/commit_history/<string:username>/<string:repo_name>")
async def commit_history_route(username, repo_name):
    try:
        access_token = await access_token_checker.check_access_token()
    except ValueError as e:
        return quart.Response(response=str(e), status=401)
    github_api = GitHubAPI(access_token)
    full_path = f"{username}/{repo_name}"
    commit_history = await github_api.get_commit_history(full_path)
    processed_commit_data = process_commit_data(commit_history)
    return quart.Response(response=json.dumps(processed_commit_data), status=200)   

@routes.post("/query_similar_code")
async def query_similar_code():
    try:
        access_token = await access_token_checker.check_access_token()
    except ValueError as e:
        return quart.Response(response=str(e), status=401)
    data = await request.get_json()
    code_snippet = data.get("code_snippet")
    top_k = data.get("top_k", 10)  # Default to returning the top 10 results
    code_embedding = get_code_embedding(code_snippet)
    similar_code_ids = query_code_embeddings_in_pinecone(code_embedding, top_k)
    # You might need to implement a method to get the code snippets from the ids
    similar_code_snippets = get_code_snippets_from_ids(similar_code_ids)
    return quart.Response(response=json.dumps(similar_code_snippets), status=200)


def process_commit_data(commit_data):
    simplified_commits = []

    for commit in commit_data:
        simplified_commit = {
            "sha": commit["sha"],
            "message": commit["commit"]["message"],
            "author": commit["commit"]["author"]["name"],
            "date": commit["commit"]["author"]["date"],
            "html_url": commit["html_url"],
        }
        simplified_commits.append(simplified_commit)

    return simplified_commits