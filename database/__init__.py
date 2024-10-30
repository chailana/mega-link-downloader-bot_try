import ast
import redis
import os

# Import the correct config based on whether you're using webhooks
if bool(os.environ.get("WEBHOOK", False)):
    from sample_config import Config
else:
    from config import Config

# Split the REDIS_URI to extract components
try:
    uri_parts = Config.REDIS_URI.split("://")[1].split("@")  # Split to get credentials and host:port
    credentials, host_port = uri_parts[0], uri_parts[1]
    username, password = credentials.split(":")  # Split credentials to get username and password
    host, port = host_port.split(":")  # Split to get host and port
    port = int(port)  # Convert port to integer
except IndexError:
    raise ValueError("Invalid REDIS_URI format. Please check your configuration.")

# Set up the Redis connection
DB = redis.StrictRedis(
    host=host,
    port=port,
    password=password,
    charset="utf-8",
    decode_responses=True,
)

def get_stuff(WHAT):
    n = []
    cha = DB.get(WHAT)
    if not cha:
        cha = "{}"
    n.append(ast.literal_eval(cha))
    return n[0]
