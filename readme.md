# Inventory Management System

An inventory management system for a small retail / e-commerce business. It consists of:

- A **Flask REST API** with CRUD operations for managing inventory
- An **OpenFoodFacts integration** to fetch product details by barcode or name
- A **CLI tool** to interact with the API from the terminal
- **Unit tests** to validate the API and external API handling

Data is stored in a temporary in-memory array (a mock database), so it resets every time the server restarts.


## Requirements

- Python 3.8 or newer
- Internet access (only needed for live OpenFoodFacts lookups; the tests run offline)

## Installation

```bash
pip install -r requirements.txt
```

## Running the Application

**1. Start the API** (keep this terminal open):

```bash
python app.py
```

The API runs at `http://127.0.0.1:5000`.

**2. Use the CLI** (in a second terminal):

```bash
python cli.py list
```

## Data Model

Each inventory item has an ID and resembles the data OpenFoodFacts returns:

| Field              | Type   | Description                         |
|--------------------|--------|-------------------------------------|
| `id`               | int    | Unique ID, assigned automatically   |
| `barcode`          | string | Product barcode                     |
| `product_name`     | string | Name of the product                 |
| `brands`           | string | Brand name                          |
| `ingredients_text` | string | Ingredients list                    |
| `price`            | float  | Selling price                       |
| `stock`            | int    | Units in stock                      |

## API Endpoints

| Method | Route                       | Description                                   | Success | Errors        |
|--------|-----------------------------|-----------------------------------------------|---------|---------------|
| GET    | `/inventory`                | Fetch all items                               | 200     | -             |
| GET    | `/inventory/<id>`           | Fetch a single item                           | 200     | 404           |
| POST   | `/inventory`                | Add a new item                                | 201     | 400           |
| PATCH  | `/inventory/<id>`           | Update an item (e.g. price or stock)          | 200     | 400, 404      |
| DELETE | `/inventory/<id>`           | Remove an item                                | 200     | 404           |
| GET    | `/external/search`          | Look up a product on OpenFoodFacts            | 200     | 400, 404, 502 |
| POST   | `/inventory/<id>/enrich`    | Fill an item's brand and ingredients from OpenFoodFacts | 200 | 404, 502 |

### Request and Response Details

**POST `/inventory`**

- Required JSON fields: `product_name`, `price`, `stock`
- Optional JSON fields: `barcode`, `brands`, `ingredients_text`
- If a `barcode` is provided and brands or ingredients are missing, the API tries to fill them in from OpenFoodFacts. If OpenFoodFacts is unavailable, the item is still saved.

```json
{
  "product_name": "Orange Juice",
  "price": 3.50,
  "stock": 20,
  "barcode": "3017620422003"
}
```

**PATCH `/inventory/<id>`**

Send only the fields you want to change:

```json
{ "price": 5.25, "stock": 30 }
```

**GET `/external/search`**

Query parameters: `barcode` or `name`.

```
GET /external/search?barcode=3017620422003
GET /external/search?name=almond milk
```

Response:

```json
{
  "product_name": "Organic Almond Milk",
  "brands": "Silk",
  "ingredients_text": "Filtered water, almonds, cane sugar"
}
```

### Error Responses

All errors return JSON in this format:

```json
{ "error": "Item not found" }
```

| Code | Meaning                                                          |
|------|------------------------------------------------------------------|
| 400  | Invalid or missing input (bad JSON, wrong types, negative values)|
| 404  | Item or external product not found                               |
| 502  | OpenFoodFacts could not be reached                               |

## CLI Usage

Make sure the API is running first.

| Task                          | Command                                                         |
|-------------------------------|-----------------------------------------------------------------|
| View all items                | `python cli.py list`                                            |
| View one item                 | `python cli.py view 1`                                          |
| Add an item                   | `python cli.py add "Orange Juice" 3.50 20`                      |
| Add an item with a barcode    | `python cli.py add "Orange Juice" 3.50 20 --barcode 3017620422003` |
| Update price and/or stock     | `python cli.py update 1 --price 5.25 --stock 30`                |
| Delete an item                | `python cli.py delete 2`                                        |
| Find a product by name (API)  | `python cli.py find --name "almond milk"`                       |
| Find a product by barcode (API)| `python cli.py find --barcode 3017620422003`                   |
| Enrich a stored item          | `python cli.py enrich 1`                                        |

### When each route is triggered

| CLI command | API route called                 |
|-------------|----------------------------------|
| `list`      | `GET /inventory`                 |
| `view`      | `GET /inventory/<id>`            |
| `add`       | `POST /inventory`                |
| `update`    | `PATCH /inventory/<id>`          |
| `delete`    | `DELETE /inventory/<id>`         |
| `find`      | `GET /external/search`           |
| `enrich`    | `POST /inventory/<id>/enrich`    |

## Error Handling

- **API:** validates required fields, data types, and negative values; returns clear error messages with proper status codes.
- **External API:** network failures and timeouts return a 502 instead of crashing. Adding an item never fails just because OpenFoodFacts is down.
- **CLI:** prints a friendly message if the API isn't running, times out, or returns an error, and exits with a non-zero status.

## Running the Tests

```bash
python -m unittest -v
```

The tests use Flask's built-in test client and mock the OpenFoodFacts calls, so they run offline. They cover:

- Fetching all items and single items 
- Adding items 
- Updating and deleting items 
- External search by barcode and name, not found, API failure, and missing parameters
- Parsing of OpenFoodFacts responses


## Data Source

Product data is provided by [Open Food Facts](https://world.openfoodfacts.org/), an open database of food products.