
"""Streamlit dashboard for the inventory monitoring system."""

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from inventory import Inventory, InventoryError, Product


# --------------------------------------------------
# 1. Project settings
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
INVENTORY_FILE = BASE_DIR / "data" / "inventory.csv"
TEMP_FILE = BASE_DIR / "data" / "inventory_temp.csv"

REQUIRED_COLUMNS = [
    "product_id",
    "name",
    "category",
    "quantity",
    "reorder_level",
    "unit_price",
]

st.set_page_config(
    page_title="Inventory Dashboard",
    page_icon="📦",
    layout="wide",
)


# --------------------------------------------------
# 2. Load inventory for the dashboard
# --------------------------------------------------

@st.cache_data
def load_inventory_data(
    file_path: str,
    modified_time: float,
) -> pd.DataFrame:
    """Load products using the existing inventory logic."""
    inventory = Inventory.from_file(file_path)

    rows = []

    for product in inventory.products:
        rows.append(
            {
                "Product ID": product.product_id,
                "Product Name": product.name,
                "Category": product.category,
                "Quantity": product.quantity,
                "Reorder Level": product.reorder_level,
                "Unit Price": product.unit_price,
                "Inventory Value": product.inventory_value,
                "Stock Status": product.stock_status,
            }
        )

    return pd.DataFrame(rows)


# --------------------------------------------------
# 3. Save changes safely to the CSV file
# --------------------------------------------------

def save_inventory_data(data: pd.DataFrame) -> None:
    """Validate the updated data and save it to the CSV file."""

    # Keep only the expected columns in their original order.
    data = data[REQUIRED_COLUMNS].copy()

    # Write to a temporary CSV first.
    data.to_csv(TEMP_FILE, index=False)

    try:
        # Check that the temporary CSV is valid before replacing
        # the original inventory file.
        Inventory.from_file(TEMP_FILE)

        # Replace the original file only after validation succeeds.
        os.replace(TEMP_FILE, INVENTORY_FILE)

    finally:
        # Remove any temporary file left behind after an error.
        if TEMP_FILE.exists():
            TEMP_FILE.unlink()

    # Clear cached data so the next page run reads the saved CSV.
    st.cache_data.clear()


def read_raw_inventory() -> pd.DataFrame:
    """Read the original CSV with the expected column names."""
    data = pd.read_csv(
        INVENTORY_FILE,
        dtype={"product_id": str},
    )

    data.columns = [
        str(column).strip().lower()
        for column in data.columns
    ]

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing:
        raise InventoryError(
            "Missing required column(s): " + ", ".join(missing)
        )

    return data[REQUIRED_COLUMNS].copy()


# --------------------------------------------------
# 4. Dashboard heading and load
# --------------------------------------------------

st.title("📦 Inventory Monitoring Dashboard")
st.caption(
    "Monitor stock, manage products, and identify items that need attention."
)

st.divider()

if not INVENTORY_FILE.exists():
    st.error(f"Inventory file not found: {INVENTORY_FILE}")
    st.stop()

try:
    inventory_df = load_inventory_data(
        str(INVENTORY_FILE),
        INVENTORY_FILE.stat().st_mtime,
    )
except Exception as exc:
    st.error(f"Could not load inventory: {exc}")
    st.stop()


# --------------------------------------------------
# 5. Summary cards
# --------------------------------------------------

total_products = len(inventory_df)
total_units = int(inventory_df["Quantity"].sum())
total_value = float(inventory_df["Inventory Value"].sum())

low_stock_count = int(
    (inventory_df["Stock Status"] == "LOW_STOCK").sum()
)

out_of_stock_count = int(
    (inventory_df["Stock Status"] == "OUT_OF_STOCK").sum()
)

alert_count = low_stock_count + out_of_stock_count

st.subheader("Inventory Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Products", f"{total_products:,}")
col2.metric("Total Units", f"{total_units:,}")
col3.metric("Inventory Value", f"₹{total_value:,.2f}")
col4.metric("Stock Alerts", f"{alert_count:,}")

st.divider()


# --------------------------------------------------
# 6. Add Product and Update Stock forms
# --------------------------------------------------

st.subheader("⚙️ Manage Inventory")

add_tab, update_tab, edit_tab, delete_tab = st.tabs(
    [
        "➕ Add Product",
        "🔄 Update Stock",
        "✏️ Edit Product",
        "🗑️ Delete Product",
    ]
)


# -------------------- Add Product --------------------

with add_tab:
    st.write("Enter the details of the new product.")

    with st.form("add_product_form"):
        new_id = st.text_input("Product ID")
        new_name = st.text_input("Product Name")
        new_category = st.text_input("Category")

        form_col1, form_col2, form_col3 = st.columns(3)

        with form_col1:
            new_quantity = st.number_input(
                "Opening Quantity",
                min_value=0,
                value=0,
                step=1,
            )

        with form_col2:
            new_reorder_level = st.number_input(
                "Reorder Level",
                min_value=0,
                value=5,
                step=1,
            )

        with form_col3:
            new_unit_price = st.number_input(
                "Unit Price (₹)",
                min_value=0.0,
                value=10.0,
                step=1.0,
                format="%.2f",
            )

        add_submitted = st.form_submit_button(
            "Add Product",
            type="primary",
        )

    if add_submitted:
        try:
            new_id = new_id.strip()
            new_name = new_name.strip()
            new_category = new_category.strip()

            if not new_id or not new_name or not new_category:
                st.error(
                    "Please fill in Product ID, Product Name, and Category."
                )

            else:
                # Product performs the existing project's validation.
                new_product = Product(
                    product_id=new_id,
                    name=new_name,
                    category=new_category,
                    quantity=int(new_quantity),
                    reorder_level=int(new_reorder_level),
                    unit_price=float(new_unit_price),
                )

                raw_data = read_raw_inventory()

                existing_ids = set(
                    raw_data["product_id"].astype(str).str.strip()
                )

                if new_id in existing_ids:
                    st.error(
                        f"Product ID '{new_id}' already exists. "
                        "Please use a unique ID."
                    )
                else:
                    new_row = pd.DataFrame(
                        [
                            {
                                "product_id": new_product.product_id,
                                "name": new_product.name,
                                "category": new_product.category,
                                "quantity": new_product.quantity,
                                "reorder_level": new_product.reorder_level,
                                "unit_price": new_product.unit_price,
                            }
                        ]
                    )

                    updated_data = pd.concat(
                        [raw_data, new_row],
                        ignore_index=True,
                    )

                    save_inventory_data(updated_data)

                    st.success(
                        f"Product '{new_name}' added successfully!"
                    )
                    st.rerun()

        except Exception as exc:
            st.error(f"Could not add product: {exc}")


# -------------------- Update Stock --------------------

with update_tab:
    st.write(
        "Choose a product and record stock received or stock removed."
    )

    if inventory_df.empty:
        st.info("There are no products to update.")
    else:
        product_options = inventory_df["Product ID"].tolist()

        with st.form("update_stock_form"):
            selected_id = st.selectbox(
                "Select Product",
                product_options,
                format_func=lambda product_id: (
                    f"{product_id} — "
                    f"{inventory_df.loc[inventory_df['Product ID'] == product_id, 'Product Name'].iloc[0]}"
                ),
            )

            selected_product = inventory_df[
                inventory_df["Product ID"] == selected_id
            ].iloc[0]

            st.info(
                f"Current quantity: {int(selected_product['Quantity'])}"
            )

            stock_action = st.radio(
                "Stock movement",
                ["Receive stock (+)", "Remove stock (-)"],
                horizontal=True,
            )

            stock_amount = st.number_input(
                "Quantity to change",
                min_value=1,
                value=1,
                step=1,
            )

            update_submitted = st.form_submit_button(
                "Save Stock Change",
                type="primary",
            )

        if update_submitted:
            try:
                raw_data = read_raw_inventory()

                matching_rows = (
                    raw_data["product_id"].astype(str).str.strip()
                    == selected_id
                )

                if not matching_rows.any():
                    st.error("The selected product was not found in the CSV.")
                else:
                    row_index = raw_data.index[matching_rows][0]

                    current_quantity = int(
                        raw_data.at[row_index, "quantity"]
                    )

                    if stock_action == "Receive stock (+)":
                        updated_quantity = (
                            current_quantity + int(stock_amount)
                        )
                    else:
                        updated_quantity = (
                            current_quantity - int(stock_amount)
                        )

                    if updated_quantity < 0:
                        st.error(
                            "You cannot remove more stock than is available."
                        )
                    else:
                        raw_data.at[row_index, "quantity"] = (
                            updated_quantity
                        )

                        save_inventory_data(raw_data)

                        st.success(
                            f"Stock updated! New quantity: "
                            f"{updated_quantity}"
                        )
                        st.rerun()

            except Exception as exc:
                st.error(f"Could not update stock: {exc}")


st.divider()


# -------------------- Edit Product --------------------

with edit_tab:
    st.write("Update the details of an existing product.")

    if inventory_df.empty:
        st.info("There are no products to edit.")
    else:
        product_options = inventory_df["Product ID"].tolist()

        selected_edit_id = st.selectbox(
            "Select product to edit",
            product_options,
            format_func=lambda product_id: (
                f"{product_id} — "
                f"{inventory_df.loc[
                    inventory_df['Product ID'] == product_id,
                    'Product Name'
                ].iloc[0]}"
            ),
            key="edit_product_selector",
        )

        selected_product = inventory_df[
            inventory_df["Product ID"] == selected_edit_id
        ].iloc[0]

        with st.form("edit_product_form"):
            edit_id = st.text_input(
                "Product ID",
                value=str(selected_product["Product ID"]),
            )

            edit_name = st.text_input(
                "Product Name",
                value=str(selected_product["Product Name"]),
            )

            edit_category = st.text_input(
                "Category",
                value=str(selected_product["Category"]),
            )

            edit_col1, edit_col2 = st.columns(2)

            with edit_col1:
                edit_reorder_level = st.number_input(
                    "Reorder Level",
                    min_value=0,
                    value=int(selected_product["Reorder Level"]),
                    step=1,
                )

            with edit_col2:
                edit_unit_price = st.number_input(
                    "Unit Price (₹)",
                    min_value=0.0,
                    value=float(selected_product["Unit Price"]),
                    step=1.0,
                    format="%.2f",
                )

            st.caption(
                "To change the quantity, use the Update Stock tab."
            )

            edit_submitted = st.form_submit_button(
                "Save Product Details",
                type="primary",
            )

        if edit_submitted:
            try:
                new_id = edit_id.strip()
                new_name = edit_name.strip()
                new_category = edit_category.strip()

                if not new_id or not new_name or not new_category:
                    st.error(
                        "Product ID, Product Name, and Category are required."
                    )
                else:
                    raw_data = read_raw_inventory()

                    matching_rows = (
                        raw_data["product_id"].astype(str).str.strip()
                        == selected_edit_id
                    )

                    if not matching_rows.any():
                        st.error(
                            "This product is no longer in the inventory."
                        )
                    else:
                        duplicate_ids = (
                            raw_data.loc[
                                raw_data.index != raw_data.index[matching_rows][0],
                                "product_id",
                            ]
                            .astype(str)
                            .str.strip()
                        )

                        if new_id in set(duplicate_ids):
                            st.error(
                                "That Product ID already exists. "
                                "Please choose a unique ID."
                            )
                        else:
                            row_index = raw_data.index[matching_rows][0]

                            quantity = int(
                                raw_data.at[row_index, "quantity"]
                            )

                            # Reuse Product validation from inventory.py.
                            updated_product = Product(
                                product_id=new_id,
                                name=new_name,
                                category=new_category,
                                quantity=quantity,
                                reorder_level=int(edit_reorder_level),
                                unit_price=float(edit_unit_price),
                            )

                            raw_data.at[row_index, "product_id"] = (
                                updated_product.product_id
                            )
                            raw_data.at[row_index, "name"] = (
                                updated_product.name
                            )
                            raw_data.at[row_index, "category"] = (
                                updated_product.category
                            )
                            raw_data.at[row_index, "reorder_level"] = (
                                updated_product.reorder_level
                            )
                            raw_data.at[row_index, "unit_price"] = (
                                updated_product.unit_price
                            )

                            save_inventory_data(raw_data)

                            st.success("Product details updated successfully!")
                            st.rerun()

            except Exception as exc:
                st.error(f"Could not edit product: {exc}")


# -------------------- Delete Product --------------------

with delete_tab:
    st.write("Remove a product from your inventory.")

    if inventory_df.empty:
        st.info("There are no products to delete.")
    else:
        delete_options = inventory_df["Product ID"].tolist()

        selected_delete_id = st.selectbox(
            "Select product to delete",
            delete_options,
            format_func=lambda product_id: (
                f"{product_id} — "
                f"{inventory_df.loc[
                    inventory_df['Product ID'] == product_id,
                    'Product Name'
                ].iloc[0]}"
            ),
            key="delete_product_selector",
        )

        delete_product = inventory_df[
            inventory_df["Product ID"] == selected_delete_id
        ].iloc[0]

        st.warning(
            f"You selected **{delete_product['Product Name']}** "
            f"(ID: {selected_delete_id}), with "
            f"{int(delete_product['Quantity'])} units in stock."
        )

        confirm_delete = st.checkbox(
            "I confirm that I want to permanently delete this product.",
            key="confirm_delete_product",
        )

        if st.button(
            "Delete Selected Product",
            type="primary",
            disabled=not confirm_delete,
        ):
            try:
                raw_data = read_raw_inventory()

                matching_rows = (
                    raw_data["product_id"].astype(str).str.strip()
                    == selected_delete_id
                )

                if not matching_rows.any():
                    st.error(
                        "This product is no longer in the inventory."
                    )
                else:
                    updated_data = raw_data.loc[
                        ~matching_rows
                    ].copy()

                    save_inventory_data(updated_data)

                    st.success(
                        f"Product '{delete_product['Product Name']}' "
                        "was deleted."
                    )
                    st.rerun()

            except Exception as exc:
                st.error(f"Could not delete product: {exc}")

# --------------------------------------------------
# 7. Low-stock alerts
# --------------------------------------------------

st.subheader("⚠️ Stock Alerts")

alert_col1, alert_col2 = st.columns(2)

alert_col1.metric("Low-Stock Products", low_stock_count)
alert_col2.metric("Out-of-Stock Products", out_of_stock_count)

alerts_df = inventory_df[
    inventory_df["Stock Status"] != "IN_STOCK"
]

if alerts_df.empty:
    st.success("All products currently have sufficient stock.")
else:
    st.warning("Some products need attention.")

    st.dataframe(
        alerts_df[
            [
                "Product ID",
                "Product Name",
                "Category",
                "Quantity",
                "Reorder Level",
                "Stock Status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.divider()


# --------------------------------------------------
# 8. Product table, search, and filters
# --------------------------------------------------

st.subheader("📋 Product Inventory")

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    search_text = st.text_input(
        "Search by product name or ID",
        placeholder="Enter product name or ID",
    )

with filter_col2:
    categories = sorted(
        inventory_df["Category"].unique().tolist()
    )

    selected_category = st.selectbox(
        "Filter by category",
        ["All Categories"] + categories,
    )

with filter_col3:
    selected_status = st.selectbox(
        "Filter by stock status",
        [
            "All Statuses",
            "IN_STOCK",
            "LOW_STOCK",
            "OUT_OF_STOCK",
        ],
    )

filtered_df = inventory_df.copy()

if search_text:
    search_mask = (
        filtered_df["Product Name"].str.contains(
            search_text,
            case=False,
            na=False,
        )
        | filtered_df["Product ID"].str.contains(
            search_text,
            case=False,
            na=False,
        )
    )

    filtered_df = filtered_df[search_mask]

if selected_category != "All Categories":
    filtered_df = filtered_df[
        filtered_df["Category"] == selected_category
    ]

if selected_status != "All Statuses":
    filtered_df = filtered_df[
        filtered_df["Stock Status"] == selected_status
    ]

st.caption(
    f"Showing {len(filtered_df)} of {total_products} products."
)

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Unit Price": st.column_config.NumberColumn(
            "Unit Price",
            format="₹%.2f",
        ),
        "Inventory Value": st.column_config.NumberColumn(
            "Inventory Value",
            format="₹%.2f",
        ),
    },
)

# Download the filtered product list.
csv_data = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download displayed products as CSV",
    data=csv_data,
    file_name="inventory_dashboard_export.csv",
    mime="text/csv",
)

st.divider()

