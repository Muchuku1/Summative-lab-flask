import argparse
import sys

import requests

BASE_URL = "http://127.0.0.1:5000"


def send_request(method, path, **kwargs):
    """Send a request to the API and handle errors in one place."""
    try:
        response = requests.request(method, BASE_URL + path, timeout=15, **kwargs)
    except requests.ConnectionError:
        print("Error: could not connect to the API. Is 'python app.py' running?")
        sys.exit(1)
    except requests.Timeout:
        print("Error: the API took too long to respond.")
        sys.exit(1)

    try:
        data = response.json()
    except ValueError:
        print("Error: the API returned an unexpected response.")
        sys.exit(1)

    if not response.ok:
        print(f"Error ({response.status_code}): {data.get('error', 'Unknown error')}")
        sys.exit(1)
    return data


def print_item(item):
    print(f"ID:          {item['id']}")
    print(f"Name:        {item['product_name']}")
    print(f"Brand:       {item['brands']}")
    print(f"Barcode:     {item['barcode']}")
    print(f"Ingredients: {item['ingredients_text']}")
    print(f"Price:       ${item['price']:.2f}")
    print(f"Stock:       {item['stock']}")
    print("-" * 40)


def cmd_list(args):
    items = send_request("GET", "/inventory")
    if not items:
        print("Inventory is empty.")
    for item in items:
        print_item(item)


def cmd_view(args):
    print_item(send_request("GET", f"/inventory/{args.id}"))


def cmd_add(args):
    body = {"product_name": args.name, "price": args.price, "stock": args.stock}
    if args.barcode:
        body["barcode"] = args.barcode
    item = send_request("POST", "/inventory", json=body)
    print("Item added:")
    print_item(item)


def cmd_update(args):
    body = {}
    if args.price is not None:
        body["price"] = args.price
    if args.stock is not None:
        body["stock"] = args.stock
    if not body:
        print("Error: provide --price and/or --stock to update.")
        sys.exit(1)
    item = send_request("PATCH", f"/inventory/{args.id}", json=body)
    print("Item updated:")
    print_item(item)


def cmd_delete(args):
    result = send_request("DELETE", f"/inventory/{args.id}")
    print(result["message"])


def cmd_find(args):
    if not args.barcode and not args.name:
        print("Error: provide --barcode or --name.")
        sys.exit(1)
    params = {}
    if args.barcode:
        params["barcode"] = args.barcode
    if args.name:
        params["name"] = args.name
    details = send_request("GET", "/external/search", params=params)
    print("Found on OpenFoodFacts:")
    print(f"Name:        {details['product_name']}")
    print(f"Brand:       {details['brands']}")
    print(f"Ingredients: {details['ingredients_text']}")


def cmd_enrich(args):
    item = send_request("POST", f"/inventory/{args.id}/enrich")
    print("Item enriched with OpenFoodFacts data:")
    print_item(item)


def build_parser():
    parser = argparse.ArgumentParser(description="Inventory CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Show all items").set_defaults(func=cmd_list)

    p = sub.add_parser("view", help="Show one item")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_view)

    p = sub.add_parser("add", help="Add a new item")
    p.add_argument("name")
    p.add_argument("price", type=float)
    p.add_argument("stock", type=int)
    p.add_argument("--barcode")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="Update price or stock")
    p.add_argument("id", type=int)
    p.add_argument("--price", type=float)
    p.add_argument("--stock", type=int)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete an item")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("find", help="Look up a product on OpenFoodFacts")
    p.add_argument("--barcode")
    p.add_argument("--name")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("enrich", help="Fill an item's details from OpenFoodFacts")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_enrich)

    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)