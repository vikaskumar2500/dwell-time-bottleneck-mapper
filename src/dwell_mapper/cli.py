import argparse

from .config import ConfigError, load_store_config


def main() -> None:
    parser = argparse.ArgumentParser(prog="dwell-map")
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate-config", help="validate a store configuration")
    validate.add_argument("path", nargs="?", default="config/store.sample.json")
    args = parser.parse_args()

    try:
        config = load_store_config(args.path)
    except ConfigError as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
    print(f"Valid configuration: {config.store_id} ({len(config.zones)} zones)")


if __name__ == "__main__":
    main()
