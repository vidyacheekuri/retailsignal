from pathlib import Path
import argparse
import json
import time
from .ingest import download, ingest
from .warehouse import build_warehouse
from .model import train, batch_score
from .insights import write_brief


def main():
    parser = argparse.ArgumentParser(description="Build RetailSignal from the UCI source")
    parser.add_argument("command", choices=["build", "score"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "score":
        if not args.input or not args.output:
            parser.error("score requires --input and --output")
        batch_score(root / "models/repeat_purchase.joblib", args.input, args.output)
        return
    start = time.monotonic()
    source = args.source or download(root)
    print("1/4 · Validate source and quarantine rejected records", flush=True)
    data, quality = ingest(root, source)
    print("2/4 · Reconcile SQL warehouse and export analysis marts", flush=True)
    build_warehouse(root, data)
    print("3/4 · Train, evaluate, and score point-in-time customer models", flush=True)
    model = train(root, data)
    print("4/4 · Write the evidence-based executive brief", flush=True)
    write_brief(root, quality, model)
    print(json.dumps({"accepted_rows": quality["accepted_rows"], "model": model["selected_model"],
                      "test_ap": model["test"]["average_precision"], "seconds": round(time.monotonic()-start, 1)}, indent=2))


if __name__ == "__main__":
    main()
