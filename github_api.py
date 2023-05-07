import httpx

class GitHubAPI:
    def __init__(self, access_token):
        self.access_token = access_token

    async def api_request(self, url):
        headers = {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        return response.json()

    async def get_repository_info(self, repo_name, properties=None):
        url = f"https://api.github.com/repos/{repo_name}"
        repo_info = await self.api_request(url)
        return {k: v for k, v in repo_info.items() if k in properties} if properties else repo_info

    async def list_repository_directory(self, username, repo_name, file_path):
        url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
        return await self.api_request(url)

    async def get_repository_file_contents(self, username, repo_name, file_path):
        url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
        return await self.api_request(url)

    async def create_issue(self, repo_name, title, body):
        url = f"https://api.github.com/repos/{repo_name}/issues"
        payload = {"title": title, "body": body}
        headers = {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
        return response.json()

    async def search_code(self, query, repo_name=None):
        url = "https://api.github.com/search/code"
        query = f"{query} repo:{repo_name}" if repo_name else query
        headers = {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params={"q": query}, headers=headers)
        return response.json()

    async def get_commit_history(self, repo_name):
        url = f"https://api.github.com/repos/{repo_name}/commits"
        headers = {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        return response.json()