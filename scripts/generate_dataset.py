import csv
import random
from datetime import datetime, timedelta

OUTPUT_FILE = "dataset/retail_sales.csv"
NUM_RECORDS = 100000

products = [
    ("Laptop", "Electronics"),
    ("Smartphone", "Electronics"),
    ("Headphones", "Electronics"),
    ("Keyboard", "Electronics"),
    ("Mouse", "Electronics"),
    ("T-Shirt", "Clothing"),
    ("Jeans", "Clothing"),
    ("Jacket", "Clothing"),
    ("Shoes", "Clothing"),
    ("Watch", "Accessories"),
    ("Backpack", "Accessories"),
    ("Sunglasses", "Accessories"),
    ("Rice", "Grocery"),
    ("Cooking Oil", "Grocery"),
    ("Biscuits", "Grocery"),
    ("Coffee", "Grocery"),
    ("Chair", "Furniture"),
    ("Table", "Furniture"),
    ("Sofa", "Furniture"),
    ("Bookshelf", "Furniture")
]

stores = [
    ("S001", "Ahmedabad", "West"),
    ("S002", "Mumbai", "West"),
    ("S003", "Pune", "West"),
    ("S004", "Bengaluru", "South"),
    ("S005", "Chennai", "South"),
    ("S006", "Hyderabad", "South"),
    ("S007", "Delhi", "North"),
    ("S008", "Jaipur", "North"),
    ("S009", "Kolkata", "East"),
    ("S010", "Bhubaneswar", "East")
]

start_date = datetime(2024, 1, 1)

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow([
        "transaction_id",
        "date",
        "store_id",
        "city",
        "region",
        "product",
        "category",
        "quantity",
        "unit_price",
        "total_amount"
    ])

    for i in range(1, NUM_RECORDS + 1):
        store_id, city, region = random.choice(stores)
        product, category = random.choice(products)

        date = start_date + timedelta(
            days=random.randint(0, 730)
        )

        quantity = random.randint(1, 10)
        unit_price = round(random.uniform(50, 50000), 2)
        total_amount = round(quantity * unit_price, 2)

        writer.writerow([
            f"T{i:06d}",
            date.strftime("%Y-%m-%d"),
            store_id,
            city,
            region,
            product,
            category,
            quantity,
            unit_price,
            total_amount
        ])

print(f"Dataset generated successfully: {OUTPUT_FILE}")
print(f"Total records: {NUM_RECORDS}")