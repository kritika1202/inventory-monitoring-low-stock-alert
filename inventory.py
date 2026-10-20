"""Core data model and calculations for the inventory monitoring project."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import logging

import pandas as pd

LOGGER = logging.getLogger(__name__)
REQUIRED_COLUMNS = [
    "product_id", "name", "category", "quantity", "reorder_level", "unit_price"
]


class InventoryError(Exception):
    """Base exception for inventory input and processing errors."""


class InventoryFileError(InventoryError):
    """Raised when an inventory file cannot be read or has the wrong format."""


class ProductValidationError(InventoryError):
    """Raised when a product row contains invalid or incomplete data."""


@dataclass(frozen=True)
class Product:
    """One product and its current stock information."""

    product_id: str
    name: str
    category: str
    quantity: int
    reorder_level: int
    unit_price: float

    def __post_init__(self) -> None:
        if not self.product_id.strip() or not self.name.strip() or not self.category.strip():
            raise ProductValidationError("Product ID, name, and category cannot be blank.")
        if self.quantity < 0:
            raise ProductValidationError("Quantity cannot be negative.")
        if self.reorder_level < 0:
            raise ProductValidationError("Reorder level cannot be negative.")
        if self.unit_price < 0:
            raise ProductValidationError("Unit price cannot be negative.")

    @property
    def inventory_value(self) -> float:
        """Value of this product's current stock."""
        return self.quantity * self.unit_price

    @property
    def stock_status(self) -> str:
        """Return OUT_OF_STOCK, LOW_STOCK, or IN_STOCK."""
        if self.quantity == 0:
            return "OUT_OF_STOCK"
        if self.quantity <= self.reorder_level:
            return "LOW_STOCK"
        return "IN_STOCK"

    
    @property
    def suggested_reorder_quantity(self) -> int:
        """Suggest enough units to reach the reorder level."""
        if self.stock_status == "IN_STOCK":
            return 0
        return max(self.reorder_level - self.quantity, 0)



class Inventory:
    """Loads products and prepares inventory summaries and reports."""

    def __init__(self, products: List[Product]):
        self.products = products
        ids = [p.product_id for p in products]
        if len(ids) != len(set(ids)):
            raise ProductValidationError("Product IDs must be unique.")

    @classmethod
    def from_file(cls, file_path: str | Path) -> "Inventory":
        """Read a .csv, .xlsx, or .xls inventory file."""
        path = Path(file_path)
        if not path.exists():
            raise InventoryFileError(f"File not found: {path}")
        suffix = path.suffix.lower()
        if suffix == ".csv":
            reader = pd.read_csv
        elif suffix in (".xlsx", ".xls"):
            reader = pd.read_excel
        else:
            raise InventoryFileError("Unsupported file type. Please use CSV or XLSX.")

        try:
            frame = reader(path)
        except Exception as exc:
            raise InventoryFileError(f"Could not read {path}: {exc}") from exc

        # Ignore surrounding spaces and accept headers in any letter case.
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise InventoryFileError("Missing required column(s): " + ", ".join(missing))

        products: List[Product] = []
        for row_number, row in frame.iterrows():
            try:
                product = Product(
                    product_id=_as_text(row["product_id"], "product_id"),
                    name=_as_text(row["name"], "name"),
                    category=_as_text(row["category"], "category"),
                    quantity=_as_int(row["quantity"], "quantity"),
                    reorder_level=_as_int(row["reorder_level"], "reorder_level"),
                    unit_price=_as_float(row["unit_price"], "unit_price"),
                )
                products.append(product)
            except (ProductValidationError, ValueError, TypeError) as exc:
                raise ProductValidationError(f"Invalid data on row {row_number + 2}: {exc}") from exc

        LOGGER.info("Loaded %d products from %s", len(products), path)
        return cls(products)

    @property
    def total_products(self) -> int:
        return len(self.products)

    @property
    def total_units(self) -> int:
        return sum(product.quantity for product in self.products)

    @property
    def total_value(self) -> float:
        return round(sum(product.inventory_value for product in self.products), 2)

    @property
    def alerts(self) -> List[Product]:
        return [p for p in self.products if p.stock_status != "IN_STOCK"]

    def category_summary(self) -> Dict[str, dict]:
        """Summarize product count, units, value, and alert count by category."""
        result: Dict[str, dict] = {}
        for product in self.products:
            summary = result.setdefault(product.category, {
                "product_count": 0, "total_units": 0, "inventory_value": 0.0,
                "alert_count": 0,
            })
            summary["product_count"] += 1
            summary["total_units"] += product.quantity
            summary["inventory_value"] += product.inventory_value
            summary["alert_count"] += product.stock_status != "IN_STOCK"
        for summary in result.values():
            summary["inventory_value"] = round(summary["inventory_value"], 2)
        return result

    def write_reports(self, output_dir: str | Path) -> None:
        """Write summary, low-stock, and category CSV reports."""
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        summary = pd.DataFrame([{
            "total_products": self.total_products,
            "total_units": self.total_units,
            "inventory_value": self.total_value,
            "low_stock_products": sum(p.stock_status == "LOW_STOCK" for p in self.products),
            "out_of_stock_products": sum(p.stock_status == "OUT_OF_STOCK" for p in self.products),
        }])
        summary.to_csv(output / "inventory_summary.csv", index=False)

        alert_rows = [{
            "product_id": p.product_id,
            "name": p.name,
            "category": p.category,
            "quantity": p.quantity,
            "reorder_level": p.reorder_level,
            "status": p.stock_status,
            "suggested_reorder_quantity": p.suggested_reorder_quantity,
            "unit_price": p.unit_price,
        } for p in self.alerts]
        pd.DataFrame(alert_rows, columns=[
            "product_id", "name", "category", "quantity", "reorder_level", "status",
            "suggested_reorder_quantity", "unit_price",
        ]).to_csv(output / "low_stock_report.csv", index=False)

        category_rows = [{"category": category, **values}
                         for category, values in self.category_summary().items()]
        pd.DataFrame(category_rows, columns=[
            "category", "product_count", "total_units", "inventory_value", "alert_count",
        ]).to_csv(output / "category_report.csv", index=False)
        LOGGER.info("Reports written to %s", output.resolve())


def _as_text(value, field_name: str) -> str:
    if pd.isna(value) or not str(value).strip():
        raise ValueError(f"{field_name} is required.")
    return str(value).strip()


def _as_int(value, field_name: str) -> int:
    number = float(value)
    if not number.is_integer():
        raise ValueError(f"{field_name} must be a whole number.")
    return int(number)


def _as_float(value, field_name: str) -> float:
    number = float(value)
    if pd.isna(number):
        raise ValueError(f"{field_name} is required.")
    return number
