"""
Realistic Dummy Data Inserter for E-Commerce Database
=====================================================
Generates and inserts at least 50 realistic rows per table.

Requirements:
    pip install sqlalchemy psycopg2-binary

Usage:
    1. Update DATABASE_URL below.
    2. Ensure tables are already created (run create_schema_orm.py first).
    3. Run: python insert_dummy_data.py
"""

import random
from datetime import datetime, timedelta, date
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker

try:
    from .create_schema_orm import Base, Customer, Product, Order, OrderItem, Payment, Review
except (ImportError, ModuleNotFoundError):
    try:
        from create_schema_orm import Base, Customer, Product, Order, OrderItem, Payment, Review
    except ModuleNotFoundError:
        from app.database.create_schema_orm import Base, Customer, Product, Order, OrderItem, Payment, Review


# ── Database Configuration ──────────────────────────────────────────────────
DB_USER = "postgres"
DB_PASSWORD = "root123"
DB_HOST = "localhost" # or remote host IP
DB_PORT = "5432"
DB_NAME = "datapilot"

# Construct the connection string
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Realistic Data Pools ────────────────────────────────────────────────────

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Frank", "Debra",
    "Alexander", "Rachel", "Raymond", "Catherine", "Patrick", "Carolyn", "Jack", "Janet",
    "Dennis", "Ruth", "Jerry", "Maria"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
    "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers",
    "Long", "Ross", "Foster", "Jimenez"
]

CITIES = [
    ("New York", "NY", "USA"), ("Los Angeles", "CA", "USA"), ("Chicago", "IL", "USA"),
    ("Houston", "TX", "USA"), ("Phoenix", "AZ", "USA"), ("Philadelphia", "PA", "USA"),
    ("San Antonio", "TX", "USA"), ("San Diego", "CA", "USA"), ("Dallas", "TX", "USA"),
    ("San Jose", "CA", "USA"), ("Austin", "TX", "USA"), ("Jacksonville", "FL", "USA"),
    ("Fort Worth", "TX", "USA"), ("Columbus", "OH", "USA"), ("Charlotte", "NC", "USA"),
    ("San Francisco", "CA", "USA"), ("Indianapolis", "IN", "USA"), ("Seattle", "WA", "USA"),
    ("Denver", "CO", "USA"), ("Washington", "DC", "USA"), ("Boston", "MA", "USA"),
    ("El Paso", "TX", "USA"), ("Nashville", "TN", "USA"), ("Detroit", "MI", "USA"),
    ("Oklahoma City", "OK", "USA"), ("Portland", "OR", "USA"), ("Las Vegas", "NV", "USA"),
    ("Louisville", "KY", "USA"), ("Baltimore", "MD", "USA"), ("Milwaukee", "WI", "USA"),
    ("Albuquerque", "NM", "USA"), ("Tucson", "AZ", "USA"), ("Fresno", "CA", "USA"),
    ("Sacramento", "CA", "USA"), ("Mesa", "AZ", "USA"), ("Kansas City", "MO", "USA"),
    ("Atlanta", "GA", "USA"), ("Long Beach", "CA", "USA"), ("Colorado Springs", "CO", "USA"),
    ("Raleigh", "NC", "USA"), ("Miami", "FL", "USA"), ("Virginia Beach", "VA", "USA"),
    ("Omaha", "NE", "USA"), ("Oakland", "CA", "USA"), ("Minneapolis", "MN", "USA"),
    ("Tulsa", "OK", "USA"), ("Arlington", "TX", "USA"), ("Wichita", "KS", "USA"),
    ("Bakersfield", "CA", "USA"), ("London", "England", "UK"), ("Manchester", "England", "UK"),
    ("Birmingham", "England", "UK"), ("Glasgow", "Scotland", "UK"), ("Edinburgh", "Scotland", "UK"),
    ("Cardiff", "Wales", "UK"), ("Toronto", "ON", "Canada"), ("Vancouver", "BC", "Canada"),
    ("Montreal", "QC", "Canada"), ("Calgary", "AB", "Canada"), ("Sydney", "NSW", "Australia"),
    ("Melbourne", "VIC", "Australia"), ("Brisbane", "QLD", "Australia"), ("Perth", "WA", "Australia"),
    ("Dublin", "Leinster", "Ireland"), ("Cork", "Munster", "Ireland"), ("Galway", "Connacht", "Ireland")
]

SEGMENTS = ["Regular", "Premium", "VIP", "New", "Inactive", "Wholesale"]

PRODUCTS_DATA = [
    ("Wireless Bluetooth Headphones", "Electronics", "Audio", 79.99, 45.00),
    ("Noise Cancelling Earbuds", "Electronics", "Audio", 129.99, 75.00),
    ("Smart Watch Pro", "Electronics", "Wearables", 249.99, 150.00),
    ("Fitness Tracker Band", "Electronics", "Wearables", 49.99, 28.00),
    ("4K Ultra HD Smart TV 55", "Electronics", "TV & Video", 599.99, 400.00),
    ("4K Ultra HD Smart TV 65", "Electronics", "TV & Video", 899.99, 600.00),
    ("Streaming Media Player", "Electronics", "TV & Video", 39.99, 22.00),
    ("Gaming Laptop 15.6", "Electronics", "Computers", 1199.99, 850.00),
    ("Ultrabook 13.3", "Electronics", "Computers", 999.99, 700.00),
    ("Wireless Mechanical Keyboard", "Electronics", "Computers", 89.99, 50.00),
    ("Ergonomic Wireless Mouse", "Electronics", "Computers", 34.99, 18.00),
    ("USB-C Hub 7-in-1", "Electronics", "Accessories", 49.99, 25.00),
    ("Portable SSD 1TB", "Electronics", "Storage", 109.99, 65.00),
    ("External Hard Drive 2TB", "Electronics", "Storage", 69.99, 40.00),
    ("Smartphone 128GB", "Electronics", "Mobile", 699.99, 450.00),
    ("Smartphone 256GB Pro", "Electronics", "Mobile", 999.99, 650.00),
    ("Wireless Charging Pad", "Electronics", "Mobile", 24.99, 12.00),
    ("Portable Power Bank 20000mAh", "Electronics", "Mobile", 39.99, 20.00),
    ("Digital Camera Mirrorless", "Electronics", "Cameras", 799.99, 550.00),
    ("Action Camera 4K", "Electronics", "Cameras", 299.99, 180.00),
    ("Drone with 4K Camera", "Electronics", "Cameras", 499.99, 320.00),
    ("Smart Home Security Camera", "Electronics", "Smart Home", 79.99, 45.00),
    ("Smart Doorbell with Camera", "Electronics", "Smart Home", 149.99, 90.00),
    ("Smart Thermostat", "Electronics", "Smart Home", 199.99, 120.00),
    ("Smart Light Bulb Kit", "Electronics", "Smart Home", 49.99, 28.00),
    ("Robot Vacuum Cleaner", "Home & Garden", "Appliances", 299.99, 180.00),
    ("Air Purifier HEPA", "Home & Garden", "Appliances", 149.99, 85.00),
    ("Espresso Machine", "Home & Garden", "Kitchen", 199.99, 120.00),
    ("Blender Pro 1200W", "Home & Garden", "Kitchen", 89.99, 50.00),
    ("Stand Mixer 5Qt", "Home & Garden", "Kitchen", 249.99, 150.00),
    ("Non-Stick Cookware Set", "Home & Garden", "Kitchen", 129.99, 75.00),
    ("Stainless Steel Knife Set", "Home & Garden", "Kitchen", 59.99, 32.00),
    ("Coffee Maker Programmable", "Home & Garden", "Kitchen", 49.99, 28.00),
    ("Electric Kettle", "Home & Garden", "Kitchen", 34.99, 18.00),
    ("Toaster 4-Slice", "Home & Garden", "Kitchen", 39.99, 22.00),
    ("Air Fryer 5.8Qt", "Home & Garden", "Kitchen", 89.99, 50.00),
    ("Instant Pot 6Qt", "Home & Garden", "Kitchen", 79.99, 45.00),
    ("Yoga Mat Premium", "Sports & Outdoors", "Fitness", 29.99, 15.00),
    ("Dumbbell Set 25lb", "Sports & Outdoors", "Fitness", 49.99, 28.00),
    ("Resistance Bands Set", "Sports & Outdoors", "Fitness", 19.99, 10.00),
    ("Treadmill Folding", "Sports & Outdoors", "Fitness", 499.99, 320.00),
    ("Mountain Bike 29", "Sports & Outdoors", "Cycling", 599.99, 380.00),
    ("Road Bike Carbon", "Sports & Outdoors", "Cycling", 1299.99, 850.00),
    ("Camping Tent 4-Person", "Sports & Outdoors", "Camping", 149.99, 85.00),
    ("Sleeping Bag Mummy", "Sports & Outdoors", "Camping", 59.99, 32.00),
    ("Hiking Backpack 40L", "Sports & Outdoors", "Camping", 79.99, 45.00),
    ("Running Shoes Men", "Sports & Outdoors", "Footwear", 89.99, 50.00),
    ("Running Shoes Women", "Sports & Outdoors", "Footwear", 89.99, 50.00),
    ("Tennis Racket Pro", "Sports & Outdoors", "Racquet Sports", 129.99, 75.00),
    ("Golf Club Set", "Sports & Outdoors", "Golf", 299.99, 180.00),
    ("Basketball Official", "Sports & Outdoors", "Team Sports", 29.99, 15.00),
    ("Soccer Ball Match", "Sports & Outdoors", "Team Sports", 34.99, 18.00),
    ("Leather Jacket Men", "Clothing", "Outerwear", 199.99, 120.00),
    ("Winter Coat Women", "Clothing", "Outerwear", 149.99, 85.00),
    ("Denim Jeans Slim Fit", "Clothing", "Bottoms", 59.99, 32.00),
    ("Chino Pants Classic", "Clothing", "Bottoms", 49.99, 28.00),
    ("Cotton T-Shirt Pack 3", "Clothing", "Tops", 29.99, 15.00),
    ("Polo Shirt Premium", "Clothing", "Tops", 39.99, 22.00),
    ("Hoodie Fleece", "Clothing", "Tops", 49.99, 28.00),
    ("Sneakers Casual", "Clothing", "Footwear", 69.99, 40.00),
    ("Dress Shirt Formal", "Clothing", "Tops", 44.99, 25.00),
    ("Wool Sweater", "Clothing", "Tops", 59.99, 32.00),
    ("Summer Dress Floral", "Clothing", "Dresses", 69.99, 40.00),
    ("Swimsuit One Piece", "Clothing", "Swimwear", 39.99, 22.00),
    ("Sunglasses Polarized", "Accessories", "Eyewear", 79.99, 40.00),
    ("Leather Wallet Bifold", "Accessories", "Wallets", 39.99, 20.00),
    ("Backpack Laptop", "Accessories", "Bags", 59.99, 32.00),
    ("Crossbody Bag Leather", "Accessories", "Bags", 89.99, 50.00),
    ("Wrist Watch Classic", "Accessories", "Watches", 149.99, 85.00),
    ("Perfume Eau de Parfum", "Beauty", "Fragrance", 89.99, 50.00),
    ("Skincare Set Premium", "Beauty", "Skincare", 129.99, 75.00),
    ("Hair Dryer Ionic", "Beauty", "Hair Care", 49.99, 28.00),
    ("Electric Shaver", "Beauty", "Personal Care", 79.99, 45.00),
    ("Makeup Palette", "Beauty", "Cosmetics", 54.99, 30.00),
    ("Moisturizer SPF 30", "Beauty", "Skincare", 24.99, 12.00),
    ("Shampoo & Conditioner Set", "Beauty", "Hair Care", 19.99, 10.00),
    ("Board Game Strategy", "Toys & Games", "Board Games", 39.99, 22.00),
    ("Building Blocks Set", "Toys & Games", "Building Toys", 49.99, 28.00),
    ("Remote Control Car", "Toys & Games", "Vehicles", 34.99, 18.00),
    ("Dollhouse Wooden", "Toys & Games", "Dolls", 89.99, 50.00),
    ("Science Kit Chemistry", "Toys & Games", "Educational", 29.99, 15.00),
    ("Stuffed Animal Large", "Toys & Games", "Plush", 24.99, 12.00),
    ("Puzzle 1000 Pieces", "Toys & Games", "Puzzles", 19.99, 10.00),
    ("Art Supplies Set", "Toys & Games", "Arts & Crafts", 34.99, 18.00),
    ("Fiction Novel Bestseller", "Books", "Fiction", 14.99, 8.00),
    ("Cookbook Healthy Eating", "Books", "Cooking", 24.99, 12.00),
    ("Self-Help Book", "Books", "Non-Fiction", 18.99, 10.00),
    ("Children's Picture Book", "Books", "Children", 12.99, 6.00),
    ("Science Textbook", "Books", "Education", 89.99, 50.00),
    ("History Encyclopedia", "Books", "Reference", 49.99, 28.00),
    ("Guitar Acoustic", "Music", "Instruments", 199.99, 120.00),
    ("Keyboard Piano 61-Key", "Music", "Instruments", 149.99, 85.00),
    ("Drum Set Electronic", "Music", "Instruments", 299.99, 180.00),
    ("Vinyl Record Player", "Music", "Audio Equipment", 79.99, 45.00),
    ("Bluetooth Speaker Portable", "Music", "Audio Equipment", 49.99, 28.00),
    ("Sheet Music Stand", "Music", "Accessories", 24.99, 12.00),
    ("Dog Food Premium 20lb", "Pet Supplies", "Food", 39.99, 22.00),
    ("Cat Litter Clumping", "Pet Supplies", "Litter", 19.99, 10.00),
    ("Pet Bed Large", "Pet Supplies", "Beds", 34.99, 18.00),
    ("Dog Leash Reflective", "Pet Supplies", "Accessories", 14.99, 7.00),
    ("Cat Tree Tower", "Pet Supplies", "Furniture", 59.99, 32.00),
    ("Aquarium Starter Kit", "Pet Supplies", "Fish", 49.99, 28.00),
    ("Bird Cage Large", "Pet Supplies", "Birds", 79.99, 45.00),
    ("Office Chair Ergonomic", "Office", "Furniture", 249.99, 150.00),
    ("Standing Desk Electric", "Office", "Furniture", 399.99, 250.00),
    ("Monitor 27' 4K", "Office", "Electronics", 349.99, 220.00),
    ("Desk Lamp LED", "Office", "Lighting", 29.99, 15.00),
    ("Filing Cabinet 2-Drawer", "Office", "Storage", 89.99, 50.00),
    ("Whiteboard Magnetic", "Office", "Presentation", 49.99, 28.00),
    ("Printer All-in-One", "Office", "Electronics", 129.99, 75.00),
    ("Shampoo Bar Natural", "Beauty", "Hair Care", 9.99, 5.00),
    ("Face Serum Vitamin C", "Beauty", "Skincare", 34.99, 18.00),
    ("Lipstick Set 5 Colors", "Beauty", "Cosmetics", 29.99, 15.00),
    ("Yoga Block Set", "Sports & Outdoors", "Fitness", 14.99, 7.00),
    ("Foam Roller", "Sports & Outdoors", "Fitness", 19.99, 10.00),
    ("Trekking Poles Carbon", "Sports & Outdoors", "Camping", 39.99, 22.00),
    ("Fishing Rod Combo", "Sports & Outdoors", "Fishing", 59.99, 32.00),
    ("Kayak Inflatable", "Sports & Outdoors", "Water Sports", 299.99, 180.00),
    ("Snowboard Beginner", "Sports & Outdoors", "Winter Sports", 199.99, 120.00),
    ("Ski Goggles Anti-Fog", "Sports & Outdoors", "Winter Sports", 49.99, 28.00),
    ("Baby Monitor WiFi", "Baby", "Safety", 89.99, 50.00),
    ("Diaper Bag Backpack", "Baby", "Gear", 44.99, 25.00),
    ("Stroller Lightweight", "Baby", "Gear", 149.99, 85.00),
    ("Car Seat Convertible", "Baby", "Safety", 199.99, 120.00),
    ("Baby Bottle Set", "Baby", "Feeding", 24.99, 12.00),
    ("Organic Baby Food Pouches", "Baby", "Feeding", 14.99, 7.00),
]

ORDER_STATUSES = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled", "Returned"]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East", "Africa"]

PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Cash", "UPI", "Crypto"]
PAYMENT_STATUSES = ["Pending", "Completed", "Failed", "Refunded"]

REVIEW_TEXTS = [
    "Absolutely love this product! Exceeded my expectations.",
    "Great quality for the price. Would definitely recommend.",
    "Decent product but shipping took longer than expected.",
    "Not as described. Disappointed with the quality.",
    "Amazing! Best purchase I've made this year.",
    "Good value for money. Works as advertised.",
    "Average product. Nothing special but does the job.",
    "Terrible quality. Broke after one week of use.",
    "Fantastic! Fast delivery and excellent packaging.",
    "Solid product. Would buy again.",
    "Poor customer service experience. Product is okay though.",
    "Love it! Perfect fit and exactly what I needed.",
    "Overpriced for what you get. Look elsewhere.",
    "Excellent build quality. Very satisfied.",
    "Mixed feelings. Some features work great, others not so much.",
    "Five stars! Can't imagine life without it now.",
    "Three stars. It's fine but could be better.",
    "One star. Complete waste of money.",
    "Highly recommend to anyone looking for this type of product.",
    "Surprisingly good! Didn't expect much but was pleasantly surprised.",
    "Works perfectly. Setup was easy and intuitive.",
    "Looks great but functionality is lacking.",
    "Best in class. No complaints whatsoever.",
    "Fair price, decent quality. Happy with the purchase.",
    "Disappointing. Had high hopes but it fell short.",
    "Outstanding performance! Worth every penny.",
    "Just okay. Nothing to write home about.",
    "Perfect gift idea. My friend loved it!",
    "Stopped working after a month. Very frustrating.",
    "Superb quality and fast shipping. Will order again.",
    "Not worth the hype. Save your money.",
    "Exactly as pictured. Very happy with my purchase.",
    "Great customer support helped resolve my issue quickly.",
    "Compact and efficient. Exactly what I was looking for.",
    "Flimsy construction. Feels cheap.",
    "Top notch! Professional grade quality.",
    "Satisfactory purchase. Met my basic needs.",
    "Brilliant design and user-friendly interface.",
    "Regret buying this. Should have read more reviews.",
    "Incredible durability. Still looks brand new after months.",
    "Standard quality. You get what you pay for.",
    "Life-changing product! Can't recommend enough.",
    "Mediocre at best. Expected more from this brand.",
    "Stylish and functional. A great combination.",
    "Defective unit received. Waiting for replacement.",
    "Pleasantly surprised by the attention to detail.",
    "Too complicated to use. Manual is unclear.",
    "Exceptional value. Comparable to much more expensive alternatives.",
]

# ── Data Generation Functions ───────────────────────────────────────────────

def generate_customers(n=60):
    """Generate realistic customer records."""
    customers = []
    used_emails = set()

    for i in range(n):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"

        # Generate unique email
        base_email = f"{first.lower()}.{last.lower()}"
        email = f"{base_email}@example.com"
        counter = 1
        while email in used_emails:
            email = f"{base_email}{counter}@example.com"
            counter += 1
        used_emails.add(email)

        city, state, country = random.choice(CITIES)
        signup_date = date.today() - timedelta(days=random.randint(1, 730))
        segment = random.choice(SEGMENTS)

        customers.append(Customer(
            name=name,
            email=email,
            city=city,
            state=state,
            country=country,
            signup_date=signup_date,
            customer_segment=segment
        ))
    return customers


def generate_products():
    """Generate product records from realistic product data."""
    products = []
    for name, category, subcategory, price, cost in PRODUCTS_DATA:
        # Add slight price variation for realism
        variation = random.uniform(0.9, 1.1)
        products.append(Product(
            product_name=name,
            category=category,
            subcategory=subcategory,
            price=round(price * variation, 2),
            cost=round(cost * variation, 2)
        ))
    return products


def generate_orders(customers, n=60):
    """Generate order records linked to customers."""
    orders = []
    for i in range(n):
        customer = random.choice(customers)
        order_date = datetime.now() - timedelta(days=random.randint(1, 365), hours=random.randint(0, 23))
        status = random.choices(
            ORDER_STATUSES,
            weights=[10, 15, 20, 40, 10, 5]  # More delivered, fewer cancelled/returned
        )[0]
        region = random.choice(REGIONS)

        orders.append(Order(
            customer_id=customer.customer_id,
            order_date=order_date,
            status=status,
            region=region
        ))
    return orders


def generate_order_items(orders, products, n=80):
    """Generate order item records linked to orders and products."""
    order_items = []
    for i in range(n):
        order = random.choice(orders)
        product = random.choice(products)
        quantity = random.choices([1, 2, 3, 4, 5], weights=[50, 25, 15, 7, 3])[0]
        unit_price = product.price
        discount = random.choices([0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30], weights=[60, 15, 10, 7, 4, 3, 1])[0]

        order_items.append(OrderItem(
            order_id=order.order_id,
            product_id=product.product_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=round(discount, 4)
        ))
    return order_items


def generate_payments(orders, n=60):
    """Generate payment records linked to orders."""
    payments = []
    for i in range(n):
        order = random.choice(orders)
        payment_date = order.order_date + timedelta(hours=random.randint(1, 48))
        method = random.choices(
            PAYMENT_METHODS,
            weights=[40, 25, 20, 5, 3, 5, 2]
        )[0]

        # Amount should roughly match order total (simulate)
        amount = round(random.uniform(25.00, 500.00), 2)

        status = random.choices(
            PAYMENT_STATUSES,
            weights=[5, 85, 5, 5]  # Mostly completed
        )[0]

        payments.append(Payment(
            order_id=order.order_id,
            payment_date=payment_date,
            payment_method=method,
            amount=amount,
            payment_status=status
        ))
    return payments


def generate_reviews(customers, products, n=70):
    """Generate review records linked to customers and products."""
    reviews = []
    used_pairs = set()

    for i in range(n):
        customer = random.choice(customers)
        product = random.choice(products)
        pair = (customer.customer_id, product.product_id)

        # Avoid duplicate customer-product reviews
        if pair in used_pairs:
            continue
        used_pairs.add(pair)

        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 8, 15, 30, 42])[0]
        text = random.choice(REVIEW_TEXTS) if random.random() > 0.15 else None  # 15% have no text
        review_date = datetime.now() - timedelta(days=random.randint(1, 180))

        reviews.append(Review(
            customer_id=customer.customer_id,
            product_id=product.product_id,
            rating=rating,
            review_text=text,
            review_date=review_date
        ))
    return reviews


# ── Main Insertion Logic ────────────────────────────────────────────────────

def insert_data():
    """Main function to generate and insert all dummy data."""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("GENERATING & INSERTING REALISTIC DUMMY DATA")
        print("=" * 60)

        # ── Step 1: Customers ───────────────────────────────────────────────
        print("\n[1/6] Generating customers...")
        customers = generate_customers(60)
        db.add_all(customers)
        db.commit()
        # Refresh to get assigned IDs
        for c in customers:
            db.refresh(c)
        print(f"      ✓ Inserted {len(customers)} customers")

        # ── Step 2: Products ────────────────────────────────────────────────
        print("\n[2/6] Generating products...")
        products = generate_products()
        db.add_all(products)
        db.commit()
        for p in products:
            db.refresh(p)
        print(f"      ✓ Inserted {len(products)} products")

        # ── Step 3: Orders ──────────────────────────────────────────────────
        print("\n[3/6] Generating orders...")
        orders = generate_orders(customers, 60)
        db.add_all(orders)
        db.commit()
        for o in orders:
            db.refresh(o)
        print(f"      ✓ Inserted {len(orders)} orders")

        # ── Step 4: Order Items ─────────────────────────────────────────────
        print("\n[4/6] Generating order items...")
        order_items = generate_order_items(orders, products, 80)
        db.add_all(order_items)
        db.commit()
        print(f"      ✓ Inserted {len(order_items)} order items")

        # ── Step 5: Payments ────────────────────────────────────────────────
        print("\n[5/6] Generating payments...")
        payments = generate_payments(orders, 60)
        db.add_all(payments)
        db.commit()
        print(f"      ✓ Inserted {len(payments)} payments")

        # ── Step 6: Reviews ─────────────────────────────────────────────────
        print("\n[6/6] Generating reviews...")
        reviews = generate_reviews(customers, products, 70)
        db.add_all(reviews)
        db.commit()
        print(f"      ✓ Inserted {len(reviews)} reviews")

        # ── Summary ─────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("INSERTION COMPLETE!")
        print("=" * 60)
        print(f"  Customers:    {len(customers)}")
        print(f"  Products:     {len(products)}")
        print(f"  Orders:       {len(orders)}")
        print(f"  Order Items:  {len(order_items)}")
        print(f"  Payments:     {len(payments)}")
        print(f"  Reviews:      {len(reviews)}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Insertion failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    insert_data()