from pathlib import Path

def main():
    out = Path("export/IRB_report.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("IRB-ready report (stub)\n", encoding="utf-8")
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
