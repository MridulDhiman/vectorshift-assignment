import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

redis_host = os.getenv("REDIS_HOST");
redis_pwd = os.getenv("REDIS_PASSWORD");
redis_client = redis.Redis(
    host=redis_host,
    password=redis_pwd,
    port=6379,  
    ssl=True)

async def add_key_value_redis(key, value, expire=None):
    await redis_client.set(key, value)
    if expire:
        await redis_client.expire(key, expire)

async def get_value_redis(key):
    return await redis_client.get(key)

async def delete_key_redis(key):
    await redis_client.delete(key)
