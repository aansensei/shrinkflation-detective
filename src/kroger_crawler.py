# kroger_crawler.py
#
# This is the starting point of the whole project.
# The idea is simple: hit the Kroger API every week, grab product data,
# and save it to the database so we can track how prices and sizes change over time.
#
# The flow is:
#   get a token -> search products by category -> save raw JSON -> insert into DB
#
# I'm saving raw JSON to disk BEFORE doing anything with the database.
# That way if something breaks in the insert logic, I don't have to re-hit the API.
# Learned this lesson the hard way on the last project.

import requests
import os
import json
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


TOKEN_URL    = "https://api.kroger.com/v1/connect/oauth2/token"
PRODUCTS_URL = "https://api.kroger.com/v1/products"
PAGE_SIZE    = 50   # hard limit per Kroger API request
MAX_PAGES    = 5    # so max 250 products per category

# these 5 categories are the most relevant for shrinkflation --
# everyday staples where people actually remember what things cost
CATEGORIES = [
    "snacks",
    "dairy",
    "beverages",
    "household",
    "personal care",
]


def get_token():
    # Kroger uses OAuth2 client credentials -- basically trade client_id + secret
    # for a temporary token that lasts 30 minutes. No user login needed.
    # requests handles the Base64 encoding when you pass auth=()
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "scope": "product.compact",
        },
        auth=(os.getenv("KROGER_CLIENT_ID"), os.getenv("KROGER_CLIENT_SECRET")),
    )
    response.raise_for_status()
    print("Token acquired.\n")
    return response.json()["access_token"]


def fetch_category(token, category):
    # filter.term works like a search box on the Kroger website
    # pagination is 1-indexed so page 0 starts at 1, page 1 starts at 51, etc.
    # if we get a 401 mid-crawl it means the 30-min token expired,
    # so we return a flag and let main() refresh it before retrying
    headers      = {"Authorization": f"Bearer {token}"}
    all_products = []
    token_expired = False

    for page in range(MAX_PAGES):
        params = {
            "filter.term":  category,
            "filter.limit": PAGE_SIZE,
            "filter.start": page * PAGE_SIZE + 1,
        }

        response = requests.get(PRODUCTS_URL, headers=headers, params=params)

        if response.status_code == 401:
            print(f"  Token expired mid-crawl on '{category}'. Will refresh.")
            token_expired = True
            break

        response.raise_for_status()
        batch = response.json().get("data", [])
        all_products.extend(batch)

        print(f"  [{category}] page {page + 1} -> {len(batch)} products")

        if len(batch) < PAGE_SIZE:
            break  # last page, nothing more to fetch

    return all_products, token_expired


def save_raw(category, products):
    # filename includes date so we can trace which crawl produced which file
    os.makedirs("raw_data", exist_ok=True)
    filename = f"raw_data/{category.replace(' ', '_')}_{date.today()}.json"

    with open(filename, "w") as f:
        json.dump(products, f, indent=2)

    print(f"  Saved {len(products)} raw records -> {filename}")


def insert_products(engine, products, category):
    # the Kroger response structure we care about:
    #   product["productId"]          -> our deduplication key
    #   product["description"]        -> product name
    #   product["brand"]              -> brand
    #   product["items"][]["price"]["regular"] -> shelf price
    #   product["items"][]["size"]    -> raw weight string like "16 oz" or "1.5 lb"
    #
    # weight_raw stays as-is for now -- the normalization (oz -> grams etc.)
    # is Phase 2's job. For now we just want everything in the database.
    today               = date.today()
    new_products_count  = 0
    new_snapshots_count = 0

    with engine.begin() as conn:
        for product in products:
            kroger_id = product.get("productId")
            name      = product.get("description", "").strip()
            brand     = product.get("brand", "").strip()

            if not kroger_id or not name:
                continue

            result = conn.execute(text("""
                INSERT INTO products (kroger_id, name, brand, category)
                VALUES (:kroger_id, :name, :brand, :category)
                ON CONFLICT (kroger_id) DO NOTHING
                RETURNING id
            """), {"kroger_id": kroger_id, "name": name, "brand": brand, "category": category})

            row = result.fetchone()
            if row:
                product_id = row[0]
                new_products_count += 1
            else:
                # product already exists from a previous crawl, just grab its id
                row        = conn.execute(
                    text("SELECT id FROM products WHERE kroger_id = :kid"),
                    {"kid": kroger_id}
                ).fetchone()
                product_id = row[0]

            # one product can have multiple size variants, snapshot all of them
            for item in product.get("items", []):
                price      = item.get("price", {}).get("regular")
                weight_raw = item.get("size")

                conn.execute(text("""
                    INSERT INTO snapshots
                        (product_id, snapshot_date, price, weight_raw)
                    VALUES
                        (:product_id, :snapshot_date, :price, :weight_raw)
                """), {
                    "product_id":    product_id,
                    "snapshot_date": today,
                    "price":         price,
                    "weight_raw":    weight_raw,
                })
                new_snapshots_count += 1

    return new_products_count, new_snapshots_count


def main():
    print(f"Shrinkflation Detective -- Crawler v1")
    print(f"Crawl date: {date.today()}\n")

    token  = get_token()
    engine = create_engine(os.getenv("NEON_DB_URL"))

    total_products  = 0
    total_snapshots = 0

    for category in CATEGORIES:
        print(f"Crawling: {category}")
        products, token_expired = fetch_category(token, category)

        if token_expired:
            token       = get_token()
            products, _ = fetch_category(token, category)

        save_raw(category, products)

        new_p, new_s     = insert_products(engine, products, category)
        total_products  += new_p
        total_snapshots += new_s

        print(f"  -> {new_p} new products | {new_s} snapshots inserted\n")

    print(f"Done. {total_products} new products, {total_snapshots} snapshots total.")


if __name__ == "__main__":
    main()
