from src.graph.neo4j.driver import get_driver

def main():
    drv = get_driver()
    with drv.session() as s:
        val = s.run("RETURN 1 AS ok").single()["ok"]
        print(f"Connected. RETURN 1 -> {val}")

if __name__ == "__main__":
    main()
