import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# MOCK DATABASE (an array of dictionaries that simulates storage)
# Each item has an ID. The shape resembles what OpenFoodFacts returns
# (product_name, brands, ingredients_text) plus our own fields (price, stock).
# ---------------------------------------------------------------------------
inventory = [
    {
        "id": 1,
        "barcode": "5000112637922",
        "product_name": "Coconut Water",
        "brands": "Vita Coco",
        "ingredients_text": "Coconut water, natural flavour",
        "price": 2.75,
        "stock": 60,
    },
    {
        "id": 2,
        "barcode": "8076800195057",
        "product_name": "Penne Rigate Pasta",
        "brands": "Barilla",
        "ingredients_text": "Durum wheat semolina, water",
        "price": 1.89,
        "stock": 80,
    },
    {
        "id": 3,
        "barcode": "7622210449283",
        "product_name": "Dark Chocolate Bar",
        "brands": "Lindt",
        "ingredients_text": "Cocoa mass, sugar, cocoa butter, vanilla",
        "price": 3.25,
        "stock": 35,
    },
]

next_id = 4  


def find_item(item_id):
    for item in inventory:
        if item["id"] == item_id:
            return item
    return None


HEADERS = {"User-Agent": "InventoryApp/1.0 (student project)"}


def fetch_product_details(barcode=None, name=None):
    if barcode:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != 1:
            return None
        product = data["product"]
    elif name:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 1,
        }
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        products = response.json().get("products", [])
        if not products:
            return None
        product = products[0]
    else:
        return None

    return {
        "product_name": product.get("product_name", ""),
        "brands": product.get("brands", ""),
        "ingredients_text": product.get("ingredients_text", ""),
    }


# GET /inventory -> fetch all items
@app.route("/inventory", methods=["GET"])
def get_all_items():
    return jsonify(inventory), 200


# GET /inventory/<id> -> fetch a single item
@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item), 200


@app.route("/inventory", methods=["POST"])
def add_item():
    global next_id
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    # Validate required fields
    for field in ("product_name", "price", "stock"):
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Validate types and values
    try:
        price = float(data["price"])
        stock = int(data["stock"])
    except (ValueError, TypeError):
        return jsonify({"error": "price must be a number and stock must be a whole number"}), 400

    if price < 0 or stock < 0:
        return jsonify({"error": "price and stock cannot be negative"}), 400

    new_item = {
        "id": next_id,
        "barcode": data.get("barcode", ""),
        "product_name": data["product_name"],
        "brands": data.get("brands", ""),
        "ingredients_text": data.get("ingredients_text", ""),
        "price": price,
        "stock": stock,
    }

    # Enhance with external data if we have a barcode
    if new_item["barcode"] and not (new_item["brands"] and new_item["ingredients_text"]):
        try:
            details = fetch_product_details(barcode=new_item["barcode"])
            if details:
                new_item["brands"] = new_item["brands"] or details["brands"]
                new_item["ingredients_text"] = new_item["ingredients_text"] or details["ingredients_text"]
        except requests.RequestException:
            pass  # The external API failing should not stop us adding the item

    inventory.append(new_item)
    next_id += 1
    return jsonify(new_item), 201


# PATCH /inventory/<id> -> update part of an item (e.g. price or stock)
@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    allowed = ["product_name", "brands", "ingredients_text", "barcode", "price", "stock"]
    for key, value in data.items():
        if key not in allowed:
            return jsonify({"error": f"Cannot update field: {key}"}), 400
        if key == "price":
            try:
                value = float(value)
            except (ValueError, TypeError):
                return jsonify({"error": "price must be a number"}), 400
            if value < 0:
                return jsonify({"error": "price cannot be negative"}), 400
        if key == "stock":
            try:
                value = int(value)
            except (ValueError, TypeError):
                return jsonify({"error": "stock must be a whole number"}), 400
            if value < 0:
                return jsonify({"error": "stock cannot be negative"}), 400
        item[key] = value

    return jsonify(item), 200


# DELETE /inventory/<id> -> remove an item
@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    inventory.remove(item)
    return jsonify({"message": "Item deleted"}), 200



@app.route("/external/search", methods=["GET"])
def external_search():
    barcode = request.args.get("barcode")
    name = request.args.get("name")

    if not barcode and not name:
        return jsonify({"error": "Provide a barcode or a name"}), 400

    try:
        details = fetch_product_details(barcode=barcode, name=name)
    except requests.RequestException:
        return jsonify({"error": "Could not reach the OpenFoodFacts API"}), 502

    if details is None:
        return jsonify({"error": "Product not found on OpenFoodFacts"}), 404
    return jsonify(details), 200


# POST /inventory/<id>/enrich -> fill an item's details from OpenFoodFacts
@app.route("/inventory/<int:item_id>/enrich", methods=["POST"])
def enrich_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    try:
        if item["barcode"]:
            details = fetch_product_details(barcode=item["barcode"])
        else:
            details = fetch_product_details(name=item["product_name"])
    except requests.RequestException:
        return jsonify({"error": "Could not reach the OpenFoodFacts API"}), 502

    if details is None:
        return jsonify({"error": "Product not found on OpenFoodFacts"}), 404

    item["brands"] = details["brands"] or item["brands"]
    item["ingredients_text"] = details["ingredients_text"] or item["ingredients_text"]
    return jsonify(item), 200


if __name__ == "__main__":
    app.run(debug=True)