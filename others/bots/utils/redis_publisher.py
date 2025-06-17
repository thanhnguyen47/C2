import json
import redis.asyncio as redis

async def publish_result(bot_id, result):
    redis_client = redis.Redis(host="redis", port=6379, db=0)
    await redis_client.publish(f"bot_results:{bot_id}", json.dumps(result))
    await redis_client.close()