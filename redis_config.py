import redis
from dotenv import load_dotenv
import os
import ssl
import certifi

load_dotenv()

redis_url = os.getenv("REDIS_HOST")
redis_pass = os.getenv("REDIS_PASS")

r = redis.Redis(
  host=redis_url,
  port=6379,
  password=redis_pass,
  ssl=True
)
try:
    pong = r.ping()
    print("✅ Redis connected:", pong)
except redis.exceptions.ConnectionError as e:
    print("❌ Redis connection failed:", e)
# r = redis.Redis(
#   host=redis_url,
#   port=6379,
#   password=redis_url,
#   ssl_cert_reqs=ssl.CERT_NONE
# )
 # reconnect
