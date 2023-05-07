import aioredis

class AccessTokenChecker:
    def __init__(self, redis_url="redis://localhost"):
        self.redis = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def set_state(self, state):
        return await self.redis.set("state", state)

    async def get_state(self):
        return await self.redis.get("state")

    async def set_access_token(self, access_token):
        return await self.redis.set("access_token", access_token)

    async def get_access_token(self):
        return await self.redis.get("access_token")

    async def check_access_token(self):
        access_token = await self.get_access_token()
        if access_token is None:
            raise ValueError('User access token not found')
        return access_token
