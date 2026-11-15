import unittest
from unittest.mock import patch

import requests

import app as app_module


class InventoryApiTests(unittest.TestCase):
    def setUp(self):
        # Fresh data before every test so tests don't affect each other
        app_module.inventory.clear()
        app_module.inventory.extend([
            {"id": 1, "barcode": "111", "product_name": "Milk", "brands": "A",
             "ingredients_text": "milk", "price": 2.0, "stock": 10},
            {"id": 2, "barcode": "222", "product_name": "Bread", "brands": "B",
             "ingredients_text": "flour", "price": 1.5, "stock": 5},
        ])
        app_module.next_id = 3
        self.client = app_module.app.test_client()

    # ---- GET ----
    def test_get_all_items(self):
        response = self.client.get("/inventory")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 2)

    def test_get_single_item(self):
        response = self.client.get("/inventory/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["product_name"], "Milk")

    def test_get_missing_item_returns_404(self):
        self.assertEqual(self.client.get("/inventory/99").status_code, 404)

    # ---- POST ----
    def test_add_item(self):
        response = self.client.post("/inventory", json={
            "product_name": "Eggs", "price": 3.0, "stock": 12})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["id"], 3)
        self.assertEqual(len(app_module.inventory), 3)

    def test_add_item_missing_field(self):
        response = self.client.post("/inventory", json={"product_name": "Eggs"})
        self.assertEqual(response.status_code, 400)

    def test_add_item_invalid_price(self):
        response = self.client.post("/inventory", json={
            "product_name": "Eggs", "price": "abc", "stock": 1})
        self.assertEqual(response.status_code, 400)

    def test_add_item_negative_stock(self):
        response = self.client.post("/inventory", json={
            "product_name": "Eggs", "price": 1, "stock": -5})
        self.assertEqual(response.status_code, 400)

    @patch("app.fetch_product_details")
    def test_add_item_with_barcode_is_enriched(self, mock_fetch):
        mock_fetch.return_value = {"product_name": "x", "brands": "Silk",
                                   "ingredients_text": "water, almonds"}
        response = self.client.post("/inventory", json={
            "product_name": "Almond Milk", "price": 5, "stock": 3, "barcode": "999"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["brands"], "Silk")

    @patch("app.fetch_product_details", side_effect=requests.ConnectionError)
    def test_add_item_still_works_if_api_down(self, mock_fetch):
        response = self.client.post("/inventory", json={
            "product_name": "Almond Milk", "price": 5, "stock": 3, "barcode": "999"})
        self.assertEqual(response.status_code, 201)

    # ---- PATCH ----
    def test_update_price_and_stock(self):
        response = self.client.patch("/inventory/1", json={"price": 9.99, "stock": 50})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["price"], 9.99)
        self.assertEqual(response.get_json()["stock"], 50)

    def test_update_missing_item(self):
        self.assertEqual(self.client.patch("/inventory/99", json={"price": 1}).status_code, 404)

    def test_update_invalid_field(self):
        response = self.client.patch("/inventory/1", json={"id": 100})
        self.assertEqual(response.status_code, 400)

    # ---- DELETE ----
    def test_delete_item(self):
        response = self.client.delete("/inventory/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(app_module.inventory), 1)

    def test_delete_missing_item(self):
        self.assertEqual(self.client.delete("/inventory/99").status_code, 404)

    # ---- External API ----
    @patch("app.fetch_product_details")
    def test_external_search_by_barcode(self, mock_fetch):
        mock_fetch.return_value = {"product_name": "Organic Almond Milk",
                                   "brands": "Silk", "ingredients_text": "water"}
        response = self.client.get("/external/search?barcode=123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["brands"], "Silk")

    @patch("app.fetch_product_details", return_value=None)
    def test_external_search_not_found(self, mock_fetch):
        self.assertEqual(self.client.get("/external/search?name=zzz").status_code, 404)

    @patch("app.fetch_product_details", side_effect=requests.ConnectionError)
    def test_external_search_api_failure(self, mock_fetch):
        self.assertEqual(self.client.get("/external/search?barcode=1").status_code, 502)

    def test_external_search_no_params(self):
        self.assertEqual(self.client.get("/external/search").status_code, 400)


class FetchProductDetailsTests(unittest.TestCase):
    @patch("app.requests.get")
    def test_barcode_lookup_parses_response(self, mock_get):
        mock_get.return_value.json.return_value = {
            "status": 1,
            "product": {"product_name": "Organic Almond Milk", "brands": "Silk",
                        "ingredients_text": "Filtered water, almonds, cane sugar"},
        }
        result = app_module.fetch_product_details(barcode="123")
        self.assertEqual(result["brands"], "Silk")

    @patch("app.requests.get")
    def test_barcode_not_found(self, mock_get):
        mock_get.return_value.json.return_value = {"status": 0}
        self.assertIsNone(app_module.fetch_product_details(barcode="000"))


if __name__ == "__main__":
    unittest.main()