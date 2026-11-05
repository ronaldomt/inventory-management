"""
Tests for restocking order API endpoints.
"""
from datetime import datetime

import pytest

import main


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Restock orders live in memory, so reset them around every test."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


class TestDemandCostFields:
    """Test suite for the cost fields the restocking tab depends on."""

    def test_every_demand_item_has_cost_and_lead_time(self, client):
        """Every demand forecast must be priceable, or it cannot be restocked."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        for item in response.json():
            assert item["unit_cost"] is not None and item["unit_cost"] > 0
            assert item["lead_time_days"] is not None and item["lead_time_days"] > 0


class TestRestockingOrderEndpoints:
    """Test suite for restocking order endpoints."""

    def test_list_is_empty_at_start(self, client):
        """Test that no orders exist before anything is submitted."""
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_order(self, client):
        """Test that a valid order is created and priced by the server."""
        response = client.post(
            "/api/restocking-orders",
            json={"lines": [{"sku": "WDG-001", "quantity": 10}]},
        )
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        # WDG-001 costs 42.00 per unit in demand_forecasts.json
        assert order["lines"][0]["unit_cost"] == 42
        assert order["lines"][0]["line_total"] == 420
        assert order["total_value"] == 420

    def test_lead_time_is_the_longest_line(self, client):
        """Test that the order lead time is the slowest line, not the sum or the first."""
        # FLT-405 takes 4 days, MTR-304 takes 21, GSK-203 takes 5
        response = client.post(
            "/api/restocking-orders",
            json={"lines": [
                {"sku": "FLT-405", "quantity": 1},
                {"sku": "MTR-304", "quantity": 1},
                {"sku": "GSK-203", "quantity": 1},
            ]},
        )
        assert response.status_code == 201

        order = response.json()
        assert order["lead_time_days"] == 21

        submitted = datetime.fromisoformat(order["submitted_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert (expected - submitted).days == 21

    def test_total_value_adds_up_all_lines(self, client):
        """Test that the order total is the sum of its line totals."""
        response = client.post(
            "/api/restocking-orders",
            json={"lines": [
                {"sku": "BRG-102", "quantity": 4},   # 4 x 18.50 = 74.00
                {"sku": "VLV-506", "quantity": 2},   # 2 x 85.00 = 170.00
            ]},
        )
        assert response.status_code == 201
        assert response.json()["total_value"] == 244

    def test_empty_order_is_rejected(self, client):
        """Test that an order with no lines returns 422."""
        response = client.post("/api/restocking-orders", json={"lines": []})
        assert response.status_code == 422

    @pytest.mark.parametrize("quantity", [0, -5])
    def test_non_positive_quantity_is_rejected(self, client, quantity):
        """Test that zero or negative quantities return 422."""
        response = client.post(
            "/api/restocking-orders",
            json={"lines": [{"sku": "WDG-001", "quantity": quantity}]},
        )
        assert response.status_code == 422

    def test_unknown_sku_returns_404(self, client):
        """Test that an SKU outside the demand forecast returns 404."""
        response = client.post(
            "/api/restocking-orders",
            json={"lines": [{"sku": "NOPE-999", "quantity": 1}]},
        )
        assert response.status_code == 404
        assert "NOPE-999" in response.json()["detail"]

    def test_rejected_order_is_not_stored(self, client):
        """Test that a failed request leaves no order behind."""
        client.post(
            "/api/restocking-orders",
            json={"lines": [{"sku": "WDG-001", "quantity": 1}, {"sku": "NOPE-999", "quantity": 1}]},
        )
        assert client.get("/api/restocking-orders").json() == []

    def test_list_is_newest_first(self, client):
        """Test that the list returns the latest order first."""
        first = client.post(
            "/api/restocking-orders",
            json={"lines": [{"sku": "WDG-001", "quantity": 1}]},
        ).json()
        second = client.post(
            "/api/restocking-orders",
            json={"lines": [{"sku": "BRG-102", "quantity": 1}]},
        ).json()

        orders = client.get("/api/restocking-orders").json()
        assert [o["id"] for o in orders] == [second["id"], first["id"]]
        assert first["order_number"] != second["order_number"]
