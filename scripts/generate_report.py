from pathlib import Path
import json


def main() -> None:
    results_dir = Path("results/logs")
    rows = []
    for path in results_dir.glob("*.json"):
        rows.append(json.loads(path.read_text()))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
