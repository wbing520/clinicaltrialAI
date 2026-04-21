import os
from functools import lru_cache
from neo4j import GraphDatabase, Driver
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

@lru_cache(maxsize=1)
def get_driver() -> Driver:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j")
    return GraphDatabase.driver(uri, auth=(user, password))
