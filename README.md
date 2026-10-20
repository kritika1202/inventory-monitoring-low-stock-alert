# Inventory Monitoring & Low-Stock Alert System

A beginner-friendly Python command-line project. It reads inventory from CSV or Excel, calculates stock value, detects low and out-of-stock products, groups items by category, and writes reports.

## What the project demonstrates

- OOP and data classes: Product stores product data; Inventory manages a list of products.
- Lists and dictionaries: products and alerts are lists; category summaries are dictionaries.
- Pandas: reads CSV/Excel and writes CSV reports.
- Exceptions: clear errors for missing files, unsupported types, invalid rows, and duplicate IDs.
- Logging: processing information and errors are written to logs/inventory.log.
- Tests: unit tests cover calculations, alert rules, reports, and common errors.

## Requirements

Python 3.10 or later is recommended.

## Setup

Open a terminal in the inventory_monitoring folder and run:

    python -m venv .venv

Activate the environment:

- Windows PowerShell: .venv\Scripts\Activate.ps1
- macOS/Linux: source .venv/bin/activate

Install the libraries:

    python -m pip install -r requirements.txt

## Run the sample

    python main.py

The sample input is data/inventory.csv. To use a different CSV or Excel file:

    python main.py path/to/your_inventory.xlsx

Optionally select an output folder:

    python main.py path/to/your_inventory.csv --output my_reports

## Input file columns

Use these exact column names (capitalization and surrounding spaces are ignored):

| Column | Meaning | Example |
| --- | --- | --- |
| product_id | Unique product code | P1001 |
| name | Product name | Wireless Mouse |
| category | Group such as Electronics | Electronics |
| quantity | Current number of units; whole number, zero or more | 18 |
| reorder_level | Alert threshold; whole number, zero or more | 10 |
| unit_price | Price per unit; zero or more | 599.00 |

Product IDs must be unique. Invalid data stops processing with a useful error and is recorded in the log.

## Alert rule

- Quantity 0 means OUT_OF_STOCK.
- Quantity greater than 0 and less than or equal to reorder level means LOW_STOCK.
- Quantity above reorder level means IN_STOCK.
- The suggested reorder quantity raises the current quantity to twice its reorder level. For example, quantity 2 and reorder level 5 suggests 8 units.

## Output

Running the program creates:

- reports/inventory_summary.csv — product count, units, inventory value, and alert counts
- reports/low_stock_report.csv — each low/out-of-stock product and a suggested reorder quantity
- reports/category_report.csv — product count, units, value, and alert count per category
- logs/inventory.log — run and error messages

Inventory value is quantity multiplied by unit price, summed across all products.

## Run tests

From the project folder:

    python -m unittest discover -s tests -v

## Suggested team split

- Participant 1: explain and present Product, data loading, total units, and inventory value.
- Participant 2: explain and present alert logic, category summary, reports, exception handling, logging, and tests.
