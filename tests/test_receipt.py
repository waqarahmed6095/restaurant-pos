import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from main import (BACKUP_FILES, build_kitchen_slip_text, build_receipt_text,
                  build_closing_report_text,
                  create_backup, restore_backup,
                  delete_session_order, get_session_id, get_session_orders,
                  get_sales_analytics, get_session_sales, hash_pin, load_menu_items,
                  record_session_order, record_session_sale, save_menu_items,
                  save_pin, verify_pin)
from repositories.menu_repository import \
    load_menu_items as repository_load_menu_items
from repositories.restaurant_repository import load_restaurant, save_restaurant
from repositories.sales_repository import \
    get_sales_report as repository_get_sales_report
from services.receipt_service import \
    build_receipt_text as service_build_receipt_text


class ReceiptFormattingTests(unittest.TestCase):
    def test_wraps_long_item_name_across_multiple_lines(self):
        order_items = [
            {
                "name": "RB Special Chicken Fajita Fries",
                "size": "Standard",
                "quantity": 2,
                "unit_price": 250,
                "total_price": 500,
            }
        ]

        receipt = build_receipt_text(order_items, "Indoor", "1")
        lines = receipt.splitlines()

        self.assertTrue(any("RB Special" in line for line in lines))
        self.assertTrue(any("Chicken Fajita" in line for line in lines))
        self.assertTrue(any("Fries" in line for line in lines))

    def test_omits_service_charge_when_disabled(self):
        order_items = [
            {
                "name": "Chicken Burger",
                "size": "Standard",
                "quantity": 1,
                "unit_price": 299,
                "total_price": 299,
            }
        ]

        receipt = build_receipt_text(
            order_items, "Indoor", "1", include_service_charge=False
        )
        lines = receipt.splitlines()

        self.assertFalse(any("Subtotal:" in line for line in lines))
        self.assertFalse(any("Service Charge:" in line for line in lines))
        self.assertTrue(any("TOTAL:" in line and "Rs 299.00" in line for line in lines))

    def test_item_table_uses_plain_amounts_and_summary_uses_currency(self):
        order_items = [
            {
                "name": "Chicken Burger",
                "size": "Standard",
                "quantity": 2,
                "unit_price": 299,
                "total_price": 598,
            }
        ]

        receipt = build_receipt_text(order_items, "Indoor", "1")
        item_line = next(line for line in receipt.splitlines() if "Chicken Burger" in line)

        self.assertNotIn("Rs", item_line)
        self.assertIn("Rs 598.00", receipt)


    def test_build_kitchen_slip_text(self):
        order_items = [
            {
                "name": "Chicken Burger",
                "size": "Standard",
                "quantity": 2,
                "unit_price": 299,
                "total_price": 598,
            }
        ]

        kitchen = build_kitchen_slip_text(order_items, "Indoor", "1")
        self.assertIn("KITCHEN SLIP", kitchen)
        self.assertIn("Chicken Burger", kitchen)
        self.assertIn("Standard", kitchen)
        self.assertIn("2", kitchen)
        self.assertNotIn("Subtotal", kitchen)
        self.assertNotIn("TOTAL:", kitchen)

    def test_build_closing_report_summarizes_session_orders(self):
        orders = [
            {
                "order_number": "2026-09-06-001",
                "include_service_charge": True,
                "total": 530.0,
                "items": [{"name": "Burger", "total": 500.0}],
            },
            {
                "order_number": "2026-09-06-002",
                "include_service_charge": False,
                "total": 250.0,
                "items": [{"name": "Tea", "total": 250.0}],
            },
        ]

        report = build_closing_report_text(orders, "2026-09-06")

        self.assertIn("END OF DAY REPORT", report)
        self.assertIn("Tickets:", report)
        self.assertIn("2026-09-06-001", report)
        self.assertTrue(any(line.startswith("Subtotal:") and line.endswith("Rs 750.00") for line in report.splitlines()))
        self.assertTrue(any(line.startswith("Service Charge:") and line.endswith("Rs 30.00") for line in report.splitlines()))
        self.assertTrue(any(line.startswith("TOTAL:") and line.endswith("Rs 780.00") for line in report.splitlines()))

    def test_receipts_include_order_number(self):
        order_items = [
            {
                "name": "Chicken Burger",
                "size": "Standard",
                "quantity": 1,
                "unit_price": 299,
                "total_price": 299,
            }
        ]

        receipt = build_receipt_text(
            order_items, "Indoor", "1", order_number="2026-07-06-001"
        )
        kitchen = build_kitchen_slip_text(
            order_items, "Indoor", "1", order_number="2026-07-06-001"
        )

        self.assertIn("Order No: 2026-07-06-001", receipt)
        self.assertIn("Order No: 2026-07-06-001", kitchen)

    def test_receipt_includes_configured_restaurant_details(self):
        order_items = [
            {
                "name": "Tea",
                "size": "Standard",
                "quantity": 1,
                "unit_price": 100,
                "total_price": 100,
            }
        ]

        receipt = service_build_receipt_text(
            order_items,
            "Indoor",
            "1",
            restaurant_name="Test Cafe",
            restaurant_address="1 Main Street",
            restaurant_phone="123",
            restaurant_email="test@example.com",
        )

        self.assertIn("Test Cafe", receipt)
        self.assertIn("1 Main Street", receipt)
        self.assertIn("Phone: 123", receipt)
        self.assertIn("test@example.com", receipt)

    def test_restaurant_profile_is_persisted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "restaurant.json"
            profile = {
                "name": "Test Cafe",
                "address": "1 Main Street",
                "phone": "123",
                "email": "test@example.com",
                "logo_path": "logo.png",
                "footer_path": "footer.png",
                "printer_name": "Receipt Printer",
                "service_charge": 25,
            }

            save_restaurant(profile, storage_path)

            loaded_profile = load_restaurant(storage_path)
            self.assertEqual(loaded_profile["name"], profile["name"])
            self.assertEqual(loaded_profile["address"], profile["address"])
            self.assertEqual(loaded_profile["service_charge"], 25.0)
            self.assertEqual(loaded_profile["printer_name"], "Receipt Printer")
            self.assertEqual(loaded_profile["indoor_tables"], 10)
            self.assertEqual(loaded_profile["outdoor_tables"], 25)

    def test_pin_can_be_saved_and_verified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pin_path = Path(temp_dir) / "access.pin"

            save_pin("1234", pin_path)

            self.assertEqual(pin_path.read_text(encoding="utf-8"), hash_pin("1234"))
            self.assertTrue(verify_pin("1234", pin_path))
            self.assertFalse(verify_pin("9999", pin_path))

    def test_session_id_uses_evening_to_early_morning_window(self):
        self.assertEqual(get_session_id(datetime(2026, 7, 6, 17, 0)), "2026-07-06")
        self.assertEqual(get_session_id(datetime(2026, 7, 7, 1, 30)), "2026-07-06")
        self.assertIsNone(get_session_id(datetime(2026, 7, 6, 4, 0)))

    def test_records_session_sales_in_storage_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "session_sales.json"
            first_total = record_session_sale(
                250.0, storage_path=storage_path, now=datetime(2026, 7, 6, 19, 0)
            )
            second_total = record_session_sale(
                75.0, storage_path=storage_path, now=datetime(2026, 7, 6, 21, 0)
            )
            stored_total = get_session_sales(
                storage_path=storage_path, now=datetime(2026, 7, 6, 22, 0)
            )

            self.assertEqual(first_total, 250.0)
            self.assertEqual(second_total, 325.0)
            self.assertEqual(stored_total, 325.0)

    def test_sales_report_summarizes_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "session_sales.json"
            record_session_order(
                {"total": 250.0},
                storage_path=storage_path,
                now=datetime(2026, 7, 6, 19, 0),
            )
            record_session_order(
                {"total": 75.0},
                storage_path=storage_path,
                now=datetime(2026, 7, 7, 19, 0),
            )

            report = repository_get_sales_report(storage_path)

            self.assertEqual(
                [entry["session_id"] for entry in report], ["2026-07-07", "2026-07-06"]
            )
            self.assertEqual(report[0]["order_count"], 1)
            self.assertEqual(report[1]["total"], 250.0)

    def test_sales_report_filters_by_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "session_sales.json"
            record_session_order(
                {"total": 250.0},
                storage_path=storage_path,
                now=datetime(2026, 7, 6, 19, 0),
            )
            record_session_order(
                {"total": 75.0},
                storage_path=storage_path,
                now=datetime(2026, 7, 7, 19, 0),
            )

            report = repository_get_sales_report(
                storage_path, start_date="2026-07-07", end_date="2026-07-07"
            )

            self.assertEqual(len(report), 1)
            self.assertEqual(report[0]["session_id"], "2026-07-07")
            self.assertEqual(report[0]["total"], 75.0)

    def test_sales_analytics_aggregates_items_and_sizes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "session_sales.json"
            now = datetime(2026, 9, 6, 19, 0)
            record_session_order(
                {
                    "total": 650.0,
                    "items": [
                        {"name": "Burger", "size": "Standard", "qty": 2, "total": 600.0},
                        {"name": "Tea", "size": "Small", "qty": 1, "total": 50.0},
                    ],
                },
                storage_path=storage_path,
                now=now,
            )
            record_session_order(
                {
                    "total": 300.0,
                    "items": [
                        {"name": "Burger", "size": "Standard", "qty": 1, "total": 300.0}
                    ],
                },
                storage_path=storage_path,
                now=now,
            )

            analytics = get_sales_analytics(storage_path=storage_path, start_date="2026-09-06", end_date="2026-09-06")

            self.assertEqual(analytics[0]["name"], "Burger")
            self.assertEqual(analytics[0]["quantity"], 3)
            self.assertEqual(analytics[0]["revenue"], 900.0)
            self.assertEqual(analytics[1]["name"], "Tea")

    def test_backup_and_restore_round_trip(self):
        import main

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original_paths = dict(BACKUP_FILES)
            original_backup_dir = main.BACKUP_DIR
            try:
                main.BACKUP_DIR = root / "backups"
                main.BACKUP_FILES.clear()
                for filename in ("restaurant.json", "menu_items.json", "session_sales.json", "access.pin"):
                    path = root / filename
                    path.write_text(f"original-{filename}", encoding="utf-8")
                    main.BACKUP_FILES[filename] = path

                backup_path = create_backup()
                main.BACKUP_FILES["restaurant.json"].write_text("changed", encoding="utf-8")
                restore_backup(backup_path)

                self.assertEqual(
                    main.BACKUP_FILES["restaurant.json"].read_text(encoding="utf-8"),
                    "original-restaurant.json",
                )
            finally:
                main.BACKUP_FILES.clear()
                main.BACKUP_FILES.update(original_paths)
                main.BACKUP_DIR = original_backup_dir

    def test_menu_items_are_persisted_to_a_json_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "menu_items.json"
            items = [
                {
                    "category": "Test",
                    "name": "Sample Item",
                    "size": "Standard",
                    "price": 150,
                }
            ]

            save_menu_items(items, storage_path=storage_path)
            loaded_items = load_menu_items(storage_path=storage_path)

            self.assertEqual(loaded_items, items)

    def test_loading_defaults_preserves_saved_price(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "menu_items.json"
            items = [
                {
                    "category": "Test",
                    "name": "Sample Item",
                    "size": "Standard",
                    "price": 175,
                }
            ]
            defaults = [
                {
                    "category": "Test",
                    "name": "Sample Item",
                    "size": "Standard",
                    "price": 150,
                }
            ]

            save_menu_items(items, storage_path=storage_path)
            loaded_items = repository_load_menu_items(defaults, storage_path)

            self.assertEqual(loaded_items[0]["price"], 175.0)

    def test_delete_session_order_removes_it_from_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "session_sales.json"
            now = datetime(2026, 7, 6, 19, 0)

            record_session_order(
                {
                    "total": 250.0,
                    "items": [{"name": "Burger", "qty": 1, "total": 250.0}],
                },
                storage_path=storage_path,
                now=now,
            )
            record_session_order(
                {"total": 75.0, "items": [{"name": "Tea", "qty": 1, "total": 75.0}]},
                storage_path=storage_path,
                now=now,
            )

            deleted_total = delete_session_order(0, storage_path=storage_path, now=now)
            remaining_orders = get_session_orders(storage_path=storage_path, now=now)

            self.assertEqual(deleted_total, 75.0)
            self.assertEqual(len(remaining_orders), 1)
            self.assertEqual(remaining_orders[0]["total"], 75.0)


if __name__ == "__main__":
    unittest.main()
