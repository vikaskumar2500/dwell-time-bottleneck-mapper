import argparse
import json

from .analytics import AnalyticsError, TrafficAnalyzer
from .config import ConfigError, load_store_config
from .io import ObservationError, read_observations, write_outputs
from .synthetic import generate_demo


def analyze(config_path: str, input_path: str, output_dir: str) -> dict:
    analyzer = TrafficAnalyzer(load_store_config(config_path))
    for timestamp, observations in read_observations(input_path):
        analyzer.update(timestamp, observations)
    analyzer.finalize()
    report = analyzer.report()
    write_outputs(report, analyzer.heatmap, output_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(prog="dwell-map")
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate-config", help="validate a store configuration")
    validate.add_argument("path", nargs="?", default="config/store.sample.json")
    generate = subcommands.add_parser("generate-demo", help="generate deterministic tracker observations")
    generate.add_argument("--output", default="data/sample/tracks.jsonl")
    run = subcommands.add_parser("analyze", help="analyze tracker observations")
    run.add_argument("--config", default="config/store.sample.json")
    run.add_argument("--input", default="data/sample/tracks.jsonl")
    run.add_argument("--output", default="outputs/demo")
    args = parser.parse_args()

    try:
        if args.command == "validate-config":
            config = load_store_config(args.path)
            print(f"Valid configuration: {config.store_id} ({len(config.zones)} zones)")
        elif args.command == "generate-demo":
            generate_demo(args.output)
            print(f"Demo observations written to {args.output}")
        else:
            report = analyze(args.config, args.input, args.output)
            print(json.dumps(report, indent=2))
    except (ConfigError, ObservationError, AnalyticsError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
