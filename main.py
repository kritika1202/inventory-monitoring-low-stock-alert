"""Command line entry point for the inventory monitoring application."""

import argparse
import logging
from pathlib import Path

from inventory import Inventory, InventoryError


def configure_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/inventory.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze inventory and create stock reports.")
    parser.add_argument("input_file", nargs="?", default="data/inventory.csv",
                        help="Path to inventory CSV or XLSX (default: data/inventory.csv)")
    parser.add_argument("--output", default="reports",
                        help="Folder for generated reports (default: reports)")
    args = parser.parse_args()
    configure_logging()
    logger = logging.getLogger(__name__)

    try:
        inventory = Inventory.from_file(args.input_file)
        inventory.write_reports(args.output)
        print("\nINVENTORY SUMMARY")
        print(f"Products: {inventory.total_products}")
        print(f"Units in stock: {inventory.total_units}")
        print(f"Total inventory value: {inventory.total_value:.2f}")
        print(f"Products needing attention: {len(inventory.alerts)}")
        print(f"Reports saved in: {Path(args.output).resolve()}")
        return 0
    except InventoryError as exc:
        logger.exception("Inventory processing failed")
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
