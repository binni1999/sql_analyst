"""
CRUD Operations Tester for E-Commerce Database
===============================================
Comprehensive test script for Create, Read, Update, Delete operations
using SQLAlchemy ORM on your existing PostgreSQL database.

Requirements:
    pip install sqlalchemy psycopg2-binary

Usage:
    1. Ensure create_schema_orm.py is in the same directory.
    2. Update DATABASE_URL below.
    3. Run: python crud_operations.py
"""

from datetime import datetime, date, timedelta
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, func, desc, and_, or_
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker

try:
    from .create_schema_orm import (
        Base, Customer, Product, Order, OrderItem, Payment, Review
    )
except (ImportError, ModuleNotFoundError):
    try:
        from create_schema_orm import (
            Base, Customer, Product, Order, OrderItem, Payment, Review
        )
    except ModuleNotFoundError:
        from app.database.create_schema_orm import (
            Base, Customer, Product, Order, OrderItem, Payment, Review
        )


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


def get_db():
    """Returns a new database session."""
    return SessionLocal()


# ════════════════════════════════════════════════════════════════════════════
#  CREATE OPERATIONS  (Insert new records)
# ════════════════════════════════════════════════════════════════════════════

# def test_create_customer():
#     """CREATE: Insert a new customer."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("CREATE: Adding a new customer")
#         print("=" * 60)

#         new_customer = Customer(
#             name="Test User",
#             email="test.user.crud@example.com",
#             city="San Francisco",
#             state="CA",
#             country="USA",
#             signup_date=date.today(),
#             customer_segment="New"
#         )
#         db.add(new_customer)
#         db.commit()
#         db.refresh(new_customer)

#         print(f"✓ Created Customer ID: {new_customer.customer_id}")
#         print(f"  Name: {new_customer.name}")
#         print(f"  Email: {new_customer.email}")
#         return new_customer.customer_id
#     except Exception as e:
#         db.rollback()
#         print(f"✗ Error: {e}")
#     finally:
#         db.close()


# def test_create_product():
#     """CREATE: Insert a new product."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("CREATE: Adding a new product")
#         print("=" * 60)

#         new_product = Product(
#             product_name="Test Product - Wireless Charger",
#             category="Electronics",
#             subcategory="Accessories",
#             price=29.99,
#             cost=15.00
#         )
#         db.add(new_product)
#         db.commit()
#         db.refresh(new_product)

#         print(f"✓ Created Product ID: {new_product.product_id}")
#         print(f"  Name: {new_product.product_name}")
#         print(f"  Price: ${new_product.price}")
#         return new_product.product_id
#     except Exception as e:
#         db.rollback()
#         print(f"✗ Error: {e}")
#     finally:
#         db.close()


# def test_create_order(customer_id):
#     """CREATE: Insert a new order for a customer."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("CREATE: Adding a new order")
#         print("=" * 60)

#         new_order = Order(
#             customer_id=customer_id,
#             order_date=datetime.now(),
#             status="Pending",
#             region="North America"
#         )
#         db.add(new_order)
#         db.commit()
#         db.refresh(new_order)

#         print(f"✓ Created Order ID: {new_order.order_id}")
#         print(f"  Customer ID: {new_order.customer_id}")
#         print(f"  Status: {new_order.status}")
#         return new_order.order_id
#     except Exception as e:
#         db.rollback()
#         print(f"✗ Error: {e}")
#     finally:
#         db.close()


# def test_create_order_item(order_id, product_id):
#     """CREATE: Insert an item into an order."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("CREATE: Adding an order item")
#         print("=" * 60)

#         new_item = OrderItem(
#             order_id=order_id,
#             product_id=product_id,
#             quantity=2,
#             unit_price=29.99,
#             discount=0.0
#         )
#         db.add(new_item)
#         db.commit()
#         db.refresh(new_item)

#         print(f"✓ Created Order Item ID: {new_item.order_item_id}")
#         print(f"  Order ID: {new_item.order_id}")
#         print(f"  Product ID: {new_item.product_id}")
#         print(f"  Quantity: {new_item.quantity}")
#         return new_item.order_item_id
#     except Exception as e:
#         db.rollback()
#         print(f"✗ Error: {e}")
#     finally:
#         db.close()


# def test_create_payment(order_id):
#     """CREATE: Insert a payment for an order."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("CREATE: Adding a payment")
#         print("=" * 60)

#         new_payment = Payment(
#             order_id=order_id,
#             payment_date=datetime.now(),
#             payment_method="Credit Card",
#             amount=59.98,
#             payment_status="Completed"
#         )
#         db.add(new_payment)
#         db.commit()
#         db.refresh(new_payment)

#         print(f"✓ Created Payment ID: {new_payment.payment_id}")
#         print(f"  Order ID: {new_payment.order_id}")
#         print(f"  Amount: ${new_payment.amount}")
#         return new_payment.payment_id
#     except Exception as e:
#         db.rollback()
#         print(f"✗ Error: {e}")
#     finally:
#         db.close()


# def test_create_review(customer_id, product_id):
#     """CREATE: Insert a product review."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("CREATE: Adding a review")
#         print("=" * 60)

#         new_review = Review(
#             customer_id=customer_id,
#             product_id=product_id,
#             rating=5,
#             review_text="Excellent product! Highly recommend.",
#             review_date=datetime.now()
#         )
#         db.add(new_review)
#         db.commit()
#         db.refresh(new_review)

#         print(f"✓ Created Review ID: {new_review.review_id}")
#         print(f"  Rating: {new_review.rating}/5")
#         print(f"  Review: {new_review.review_text}")
#         return new_review.review_id
#     except Exception as e:
#         db.rollback()
#         print(f"✗ Error: {e}")
#     finally:
#         db.close()


# ════════════════════════════════════════════════════════════════════════════
#  READ OPERATIONS  (Fetch / Query records)
# ════════════════════════════════════════════════════════════════════════════

def test_read_all_customers():
    """READ: Fetch all customers."""
    db = get_db()
    try:
        print("\n" + "=" * 60)
        print("READ: All Customers (first 10)")
        print("=" * 60)

        customers = db.query(Customer).limit(10).all()
        for c in customers:
            print(f"  ID:{c.customer_id:<3} | {c.name:<20} | {c.email:<30} | {c.customer_segment}")
    finally:
        db.close()


# def test_read_customer_by_id(customer_id):
#     """READ: Fetch a single customer by ID."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"READ: Customer by ID = {customer_id}")
#         print("=" * 60)

#         customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
#         if customer:
#             print(f"  Found: {customer.name} ({customer.email})")
#             print(f"  Location: {customer.city}, {customer.state}, {customer.country}")
#             print(f"  Segment: {customer.customer_segment}")
#             print(f"  Signup Date: {customer.signup_date}")
#         else:
#             print(f"  ✗ No customer found with ID {customer_id}")
#     finally:
#         db.close()


# def test_read_customers_by_segment(segment="Premium"):
#     """READ: Fetch customers filtered by segment."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"READ: Customers with segment = '{segment}'")
#         print("=" * 60)

#         customers = db.query(Customer).filter(Customer.customer_segment == segment).all()
#         print(f"  Found {len(customers)} customers:")
#         for c in customers[:5]:  # Show first 5
#             print(f"    {c.name} - {c.email}")
#         if len(customers) > 5:
#             print(f"    ... and {len(customers) - 5} more")
#     finally:
#         db.close()


# def test_read_products_by_category(category="Electronics"):
#     """READ: Fetch products filtered by category."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"READ: Products in category = '{category}'")
#         print("=" * 60)

#         products = db.query(Product).filter(Product.category == category).all()
#         print(f"  Found {len(products)} products:")
#         for p in products[:5]:
#             print(f"    {p.product_name:<35} | ${p.price:.2f}")
#         if len(products) > 5:
#             print(f"    ... and {len(products) - 5} more")
#     finally:
#         db.close()


# def test_read_orders_with_status(status="Delivered"):
#     """READ: Fetch orders by status."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"READ: Orders with status = '{status}'")
#         print("=" * 60)

#         orders = db.query(Order).filter(Order.status == status).all()
#         print(f"  Found {len(orders)} orders:")
#         for o in orders[:5]:
#             print(f"    Order #{o.order_id} | Customer #{o.customer_id} | {o.order_date.strftime('%Y-%m-%d')} | {o.region}")
#         if len(orders) > 5:
#             print(f"    ... and {len(orders) - 5} more")
#     finally:
#         db.close()


# def test_read_orders_with_customer():
#     """READ: Fetch orders with customer details (JOIN)."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("READ: Orders with Customer Names (JOIN)")
#         print("=" * 60)

#         results = db.query(Order, Customer).join(Customer, Order.customer_id == Customer.customer_id).limit(5).all()
#         for order, customer in results:
#             print(f"  Order #{order.order_id:<3} | {customer.name:<20} | {order.status:<12} | {order.region}")
#     finally:
#         db.close()


# def test_read_order_items_with_products():
#     """READ: Fetch order items with product details (JOIN)."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("READ: Order Items with Product Details (JOIN)")
#         print("=" * 60)

#         results = db.query(OrderItem, Product).join(Product, OrderItem.product_id == Product.product_id).limit(5).all()
#         for item, product in results:
#             print(f"  Item #{item.order_item_id:<3} | {product.product_name:<30} | Qty:{item.quantity} | ${item.unit_price:.2f}")
#     finally:
#         db.close()


# def test_read_payments_with_orders():
#     """READ: Fetch payments with order details (JOIN)."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("READ: Payments with Order Details (JOIN)")
#         print("=" * 60)

#         results = db.query(Payment, Order).join(Order, Payment.order_id == Order.order_id).limit(5).all()
#         for payment, order in results:
#             print(f"  Payment #{payment.payment_id:<3} | Order #{order.order_id} | ${payment.amount:.2f} | {payment.payment_method} | {payment.payment_status}")
#     finally:
#         db.close()


# def test_read_reviews_with_customer_and_product():
#     """READ: Fetch reviews with customer and product details (Multiple JOINs)."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("READ: Reviews with Customer & Product (Multiple JOINs)")
#         print("=" * 60)

#         results = db.query(Review, Customer, Product).            join(Customer, Review.customer_id == Customer.customer_id).            join(Product, Review.product_id == Product.product_id).            limit(5).all()
#         for review, customer, product in results:
#             print(f"  Review #{review.review_id:<3} | {customer.name:<18} rated '{product.product_name[:25]}' {review.rating}/5")
#     finally:
#         db.close()


# def test_read_aggregation():
#     """READ: Aggregation queries (COUNT, SUM, AVG)."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("READ: Aggregation Queries")
#         print("=" * 60)

#         # Total customers
#         total_customers = db.query(func.count(Customer.customer_id)).scalar()
#         print(f"  Total Customers: {total_customers}")

#         # Total products
#         total_products = db.query(func.count(Product.product_id)).scalar()
#         print(f"  Total Products: {total_products}")

#         # Total orders
#         total_orders = db.query(func.count(Order.order_id)).scalar()
#         print(f"  Total Orders: {total_orders}")

#         # Average product price
#         avg_price = db.query(func.avg(Product.price)).scalar()
#         print(f"  Average Product Price: ${avg_price:.2f}")

#         # Total revenue from payments
#         total_revenue = db.query(func.sum(Payment.amount)).scalar()
#         print(f"  Total Payment Amount: ${total_revenue:.2f}")

#         # Average review rating
#         avg_rating = db.query(func.avg(Review.rating)).scalar()
#         print(f"  Average Review Rating: {avg_rating:.2f}/5")

#         # Orders by status
#         print("\n  Orders by Status:")
#         status_counts = db.query(Order.status, func.count(Order.order_id)).group_by(Order.status).all()
#         for status, count in status_counts:
#             print(f"    {status:<12}: {count}")

#         # Top 5 customers by order count
#         print("\n  Top 5 Customers by Order Count:")
#         top_customers = db.query(Customer.name, func.count(Order.order_id).label('order_count')).            join(Order, Customer.customer_id == Order.customer_id).            group_by(Customer.customer_id).            order_by(desc('order_count')).            limit(5).all()
#         for name, count in top_customers:
#             print(f"    {name:<20}: {count} orders")
#     finally:
#         db.close()


# def test_read_search():
#     """READ: Search queries with LIKE / partial matching."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("READ: Search Queries")
#         print("=" * 60)

#         # Search customers by name (partial match)
#         search_term = "John"
#         customers = db.query(Customer).filter(Customer.name.ilike(f"%{search_term}%")).all()
#         print(f"  Customers matching '{search_term}': {len(customers)}")
#         for c in customers[:3]:
#             print(f"    {c.name} - {c.email}")

#         # Search products by name
#         search_term = "Wireless"
#         products = db.query(Product).filter(Product.product_name.ilike(f"%{search_term}%")).all()
#         print(f"\n  Products matching '{search_term}': {len(products)}")
#         for p in products[:3]:
#             print(f"    {p.product_name} - ${p.price:.2f}")

#         # Complex filter: Customers from USA who signed up in last year
#         one_year_ago = date.today() - timedelta(days=365)
#         customers = db.query(Customer).filter(
#             and_(Customer.country == "USA", Customer.signup_date >= one_year_ago)
#         ).all()
#         print(f"\n  USA customers signed up in last year: {len(customers)}")
#     finally:
#         db.close()


# # ════════════════════════════════════════════════════════════════════════════
# #  UPDATE OPERATIONS  (Modify existing records)
# # ════════════════════════════════════════════════════════════════════════════

# def test_update_customer(customer_id):
#     """UPDATE: Modify a customer's segment and city."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"UPDATE: Customer ID = {customer_id}")
#         print("=" * 60)

#         customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
#         if customer:
#             print(f"  Before: {customer.name} | Segment: {customer.customer_segment} | City: {customer.city}")

#             customer.customer_segment = "VIP"
#             customer.city = "Updated City"
#             db.commit()
#             db.refresh(customer)

#             print(f"  After:  {customer.name} | Segment: {customer.customer_segment} | City: {customer.city}")
#             print("  ✓ Update successful")
#         else:
#             print(f"  ✗ Customer {customer_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# def test_update_order_status(order_id):
#     """UPDATE: Change an order's status."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"UPDATE: Order ID = {order_id} - Change Status")
#         print("=" * 60)

#         order = db.query(Order).filter(Order.order_id == order_id).first()
#         if order:
#             old_status = order.status
#             order.status = "Shipped"
#             db.commit()
#             db.refresh(order)

#             print(f"  Order #{order_id}: {old_status} → {order.status}")
#             print("  ✓ Update successful")
#         else:
#             print(f"  ✗ Order {order_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# def test_update_product_price(product_id):
#     """UPDATE: Update a product's price."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"UPDATE: Product ID = {product_id} - Change Price")
#         print("=" * 60)

#         product = db.query(Product).filter(Product.product_id == product_id).first()
#         if product:
#             old_price = product.price
#             product.price = round(old_price * 1.10, 2)  # 10% price increase
#             db.commit()
#             db.refresh(product)

#             print(f"  Product: {product.product_name}")
#             print(f"  Price: ${old_price:.2f} → ${product.price:.2f}")
#             print("  ✓ Update successful")
#         else:
#             print(f"  ✗ Product {product_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# def test_bulk_update():
#     """UPDATE: Bulk update - mark all Pending orders older than 7 days as Processing."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("UPDATE: Bulk Update - Old Pending Orders → Processing")
#         print("=" * 60)

#         seven_days_ago = datetime.now() - timedelta(days=7)

#         count = db.query(Order).filter(
#             and_(Order.status == "Pending", Order.order_date < seven_days_ago)
#         ).update({Order.status: "Processing"}, synchronize_session=False)

#         db.commit()
#         print(f"  ✓ Updated {count} orders from Pending to Processing")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# # ════════════════════════════════════════════════════════════════════════════
# #  DELETE OPERATIONS  (Remove records)
# # ════════════════════════════════════════════════════════════════════════════

# def test_delete_review(review_id):
#     """DELETE: Remove a specific review."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"DELETE: Review ID = {review_id}")
#         print("=" * 60)

#         review = db.query(Review).filter(Review.review_id == review_id).first()
#         if review:
#             db.delete(review)
#             db.commit()
#             print(f"  ✓ Review {review_id} deleted successfully")
#         else:
#             print(f"  ✗ Review {review_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# def test_delete_payment(payment_id):
#     """DELETE: Remove a specific payment."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"DELETE: Payment ID = {payment_id}")
#         print("=" * 60)

#         payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
#         if payment:
#             db.delete(payment)
#             db.commit()
#             print(f"  ✓ Payment {payment_id} deleted successfully")
#         else:
#             print(f"  ✗ Payment {payment_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# def test_delete_order_item(order_item_id):
#     """DELETE: Remove an order item."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"DELETE: Order Item ID = {order_item_id}")
#         print("=" * 60)

#         item = db.query(OrderItem).filter(OrderItem.order_item_id == order_item_id).first()
#         if item:
#             db.delete(item)
#             db.commit()
#             print(f"  ✓ Order Item {order_item_id} deleted successfully")
#         else:
#             print(f"  ✗ Order Item {order_item_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# def test_delete_order_and_cascade(order_id):
#     """DELETE: Remove an order (cascades to order_items and payments)."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"DELETE: Order ID = {order_id} (with CASCADE)")
#         print("=" * 60)

#         # Count related records before delete
#         items_count = db.query(OrderItem).filter(OrderItem.order_id == order_id).count()
#         payments_count = db.query(Payment).filter(Payment.order_id == order_id).count()

#         order = db.query(Order).filter(Order.order_id == order_id).first()
#         if order:
#             db.delete(order)
#             db.commit()
#             print(f"  ✓ Order {order_id} deleted")
#             print(f"    (Cascaded: {items_count} order items, {payments_count} payments also removed)")
#         else:
#             print(f"  ✗ Order {order_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# def test_delete_customer_and_cascade(customer_id):
#     """DELETE: Remove a customer (cascades to orders and reviews)."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print(f"DELETE: Customer ID = {customer_id} (with CASCADE)")
#         print("=" * 60)

#         orders_count = db.query(Order).filter(Order.customer_id == customer_id).count()
#         reviews_count = db.query(Review).filter(Review.customer_id == customer_id).count()

#         customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
#         if customer:
#             db.delete(customer)
#             db.commit()
#             print(f"  ✓ Customer '{customer.name}' deleted")
#             print(f"    (Cascaded: {orders_count} orders, {reviews_count} reviews also removed)")
#         else:
#             print(f"  ✗ Customer {customer_id} not found")
#     except Exception as e:
#         db.rollback()
#         print(f"  ✗ Error: {e}")
#     finally:
#         db.close()


# # ════════════════════════════════════════════════════════════════════════════
# #  ADVANCED QUERIES
# # ════════════════════════════════════════════════════════════════════════════

# def test_advanced_subquery():
#     """ADVANCED: Subquery - Customers who have never placed an order."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("ADVANCED: Customers with NO orders (Subquery)")
#         print("=" * 60)

#         from sqlalchemy.orm import aliased

#         subquery = db.query(Order.customer_id).subquery()
#         customers = db.query(Customer).filter(~Customer.customer_id.in_(subquery)).all()

#         print(f"  Found {len(customers)} customers with no orders:")
#         for c in customers[:5]:
#             print(f"    {c.name} ({c.email})")
#         if len(customers) > 5:
#             print(f"    ... and {len(customers) - 5} more")
#     finally:
#         db.close()


# def test_advanced_revenue_by_region():
#     """ADVANCED: Revenue by region."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("ADVANCED: Total Revenue by Region")
#         print("=" * 60)

#         results = db.query(
#             Order.region,
#             func.sum(Payment.amount).label("total_revenue"),
#             func.count(Order.order_id).label("order_count")
#         ).join(Payment, Order.order_id == Payment.order_id).            group_by(Order.region).            order_by(desc("total_revenue")).all()

#         for region, revenue, count in results:
#             print(f"  {region:<18}: ${revenue:.2f} ({count} orders)")
#     finally:
#         db.close()


# def test_advanced_top_products():
#     """ADVANCED: Top selling products by quantity."""
#     db = get_db()
#     try:
#         print("\n" + "=" * 60)
#         print("ADVANCED: Top 5 Best-Selling Products (by quantity)")
#         print("=" * 60)

#         results = db.query(
#             Product.product_name,
#             func.sum(OrderItem.quantity).label("total_sold"),
#             func.sum(OrderItem.quantity * OrderItem.unit_price * (1 - OrderItem.discount)).label("revenue")
#         ).join(OrderItem, Product.product_id == OrderItem.product_id).            group_by(Product.product_id).            order_by(desc("total_sold")).            limit(5).all()

#         for name, qty, rev in results:
#             print(f"  {name[:35]:<35} | Sold: {qty:<4} | Revenue: ${rev:.2f}")
#     finally:
#         db.close()


# # ════════════════════════════════════════════════════════════════════════════
# #  MAIN RUNNER
# # ════════════════════════════════════════════════════════════════════════════

# def run_all_tests():
#     """Runs all CRUD tests in sequence."""

#     print("\n" + "█" * 60)
#     print("  E-COMMERCE DATABASE - CRUD OPERATIONS TEST")
#     print("█" * 60)

#     # ── CREATE ────────────────────────────────────────────────────────────
#     print("\n" + "▓" * 60)
#     print("  SECTION 1: CREATE OPERATIONS")
#     print("▓" * 60)

#     customer_id = test_create_customer()
#     product_id = test_create_product()

#     if customer_id and product_id:
#         order_id = test_create_order(customer_id)
#         order_item_id = test_create_order_item(order_id, product_id)
#         payment_id = test_create_payment(order_id)
#         review_id = test_create_review(customer_id, product_id)
#     else:
#         print("\n  Skipping dependent CREATE tests (customer/product creation failed)")
#         order_id = order_item_id = payment_id = review_id = None

#     # ── READ ──────────────────────────────────────────────────────────────
#     print("\n" + "▓" * 60)
#     print("  SECTION 2: READ OPERATIONS")
#     print("▓" * 60)

#     test_read_all_customers()
#     if customer_id:
#         test_read_customer_by_id(customer_id)
#     test_read_customers_by_segment("Premium")
#     test_read_products_by_category("Electronics")
#     test_read_orders_with_status("Delivered")
#     test_read_orders_with_customer()
#     test_read_order_items_with_products()
#     test_read_payments_with_orders()
#     test_read_reviews_with_customer_and_product()
#     test_read_aggregation()
#     test_read_search()

#     # ── UPDATE ────────────────────────────────────────────────────────────
#     print("\n" + "▓" * 60)
#     print("  SECTION 3: UPDATE OPERATIONS")
#     print("▓" * 60)

#     if customer_id:
#         test_update_customer(customer_id)
#     if order_id:
#         test_update_order_status(order_id)
#     if product_id:
#         test_update_product_price(product_id)
#     test_bulk_update()

#     # ── DELETE ────────────────────────────────────────────────────────────
#     print("\n" + "▓" * 60)
#     print("  SECTION 4: DELETE OPERATIONS")
#     print("▓" * 60)

#     if review_id:
#         test_delete_review(review_id)
#     if payment_id:
#         test_delete_payment(payment_id)
#     if order_item_id:
#         test_delete_order_item(order_item_id)
#     if order_id:
#         test_delete_order_and_cascade(order_id)
#     if customer_id:
#         test_delete_customer_and_cascade(customer_id)

#     # ── ADVANCED ──────────────────────────────────────────────────────────
#     print("\n" + "▓" * 60)
#     print("  SECTION 5: ADVANCED QUERIES")
#     print("▓" * 60)

#     test_advanced_subquery()
#     test_advanced_revenue_by_region()
#     test_advanced_top_products()

#     print("\n" + "█" * 60)
#     print("  ALL CRUD TESTS COMPLETED!")
#     print("█" * 60)


if __name__ == "__main__":
    test_read_all_customers()