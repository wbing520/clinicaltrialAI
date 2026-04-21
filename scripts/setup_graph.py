from src.graph.schema.nodes import SCHEMA_CYPHER
from src.graph.neo4j.driver import get_driver

def main():
    with get_driver().session() as s:
        for stmt in SCHEMA_CYPHER:
            s.run(stmt)
            print(f"Applied: {stmt}")

if __name__ == "__main__":
    main()
