import csv
import tempfile
import unittest
from pathlib import Path

from inventory import Inventory, InventoryFileError, Product, ProductValidationError


class ProductTests(unittest.TestCase):
    def test_stock_status_and_value(self):
        low = Product("1", "Cable", "Electronics", 2, 5, 100.0)
        empty = Product("2", "Pen", "Stationery", 0, 4, 10.0)
        normal = Product("3", "Book", "Stationery", 8, 4, 25.0)

        self.assertEqual(low.stock_status, "LOW_STOCK")
        self.assertEqual(low.inventory_value, 200.0)
        self.assertEqual(low.suggested_reorder_quantity, 8)
        self.assertEqual(empty.stock_status, "OUT_OF_STOCK")
        self.assertEqual(normal.stock_status, "IN_STOCK")
        self.assertEqual(normal.suggested_reorder_quantity, 0)

    def test_invalid_negative_quantity(self):
        with self.assertRaises(ProductValidationError):
            Product("1", "Cable", "Electronics", -1, 5, 100.0)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.csv_path = Path(self.temp_dir.name) / "inventory.csv"
        rows = [
            ["product_id", "name", "category", "quantity", "reorder_level", "unit_price"],
            ["P1", "Mouse", "Electronics", 2, 5, 100],
            ["P2", "Notebook", "Stationery", 10, 3, 20],
            ["P3", "Pen", "Stationery", 0, 4, 5],
        ]
        with self.csv_path.open("w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerows(rows)

    def test_load_and_calculations(self):
        inventory = Inventory.from_file(self.csv_path)
        self.assertEqual(inventory.total_products, 3)
        self.assertEqual(inventory.total_units, 12)
        self.assertEqual(inventory.total_value, 400.0)
        self.assertEqual(len(inventory.alerts), 2)
        self.assertEqual(inventory.category_summary()["Stationery"]["product_count"], 2)

    def test_reports_are_created(self):
        inventory = Inventory.from_file(self.csv_path)
        output = Path(self.temp_dir.name) / "reports"
        inventory.write_reports(output)
        self.assertTrue((output / "inventory_summary.csv").exists())
        self.assertTrue((output / "low_stock_report.csv").exists())
        self.assertTrue((output / "category_report.csv").exists())

    def test_missing_file_is_reported(self):
        with self.assertRaises(InventoryFileError):
            Inventory.from_file(Path(self.temp_dir.name) / "missing.csv")

    def test_duplicate_product_id_is_rejected(self):
        product = Product("P1", "Mouse", "Electronics", 1, 5, 20.0)
        with self.assertRaises(ProductValidationError):
            Inventory([product, product])


if __name__ == "__main__":
    unittest.main()
