"""
PostgreSQL Database Schema Creator using SQLAlchemy ORM
=======================================================
This script creates all tables using SQLAlchemy 2.0 ORM.

Requirements:
    pip install sqlalchemy psycopg2-binary

Usage:
    1. Update the DATABASE_URL in the config section.
    2. Run: python create_schema_orm.py
"""

from datetime import datetime, date
from typing import List, Optional

# pyrefly: ignore [missing-import]
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Date, DateTime,
    Numeric, ForeignKey, CheckConstraint, Index, Enum
)
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import (
    declarative_base, relationship, Session, sessionmaker, Mapped, mapped_column
)
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import NUMERIC

# ── Database Configuration ──────────────────────────────────────────────────
# Format: postgresql://username:password@host:port/database
# Define database connection credentials
DB_USER = "postgres"
DB_PASSWORD = "root123"
DB_HOST = "localhost" # or remote host IP
DB_PORT = "5432"
DB_NAME = "datapilot"

# Construct the connection string
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Create engine
engine = create_engine(DATABASE_URL, echo=False)  # Set echo=True to see SQL logs

# Base class for all models
Base = declarative_base()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── ORM Models ──────────────────────────────────────────────────────────────

class Customer(Base):
    """Represents a customer in the e-commerce system."""
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    signup_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    customer_segment: Mapped[Optional[str]] = mapped_column(String(50), default="Regular")

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="customer", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_customers_email", "email"),
        Index("idx_customers_segment", "customer_segment"),
        Index("idx_customers_country", "country"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.customer_id}, name='{self.name}', email='{self.email}')>"


class Product(Base):
    """Represents a product available for purchase."""
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(NUMERIC(12, 2), nullable=False)
    cost: Mapped[float] = mapped_column(NUMERIC(12, 2), nullable=False)

    # Relationships
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="product")

    # Constraints & Indexes
    __table_args__ = (
        CheckConstraint("price >= 0", name="chk_products_price_nonnegative"),
        CheckConstraint("cost >= 0", name="chk_products_cost_nonnegative"),
        Index("idx_products_category", "category"),
        Index("idx_products_subcategory", "subcategory"),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.product_id}, name='{self.product_name}', category='{self.category}')>"


class Order(Base):
    """Represents a customer order."""
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Pending"
    )
    region: Mapped[Optional[str]] = mapped_column(String(100))

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order", cascade="all, delete-orphan")

    # Constraints & Indexes
    __table_args__ = (
        CheckConstraint(
            "status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled', 'Returned')",
            name="chk_orders_status"
        ),
        Index("idx_orders_customer_id", "customer_id"),
        Index("idx_orders_order_date", "order_date"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_region", "region"),
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.order_id}, customer_id={self.customer_id}, status='{self.status}')>"


class OrderItem(Base):
    """Represents a line item within an order."""
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(NUMERIC(12, 2), nullable=False)
    discount: Mapped[float] = mapped_column(NUMERIC(5, 4), nullable=False, default=0.0)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")

    # Constraints & Indexes
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="chk_order_items_price_nonnegative"),
        CheckConstraint("discount >= 0 AND discount <= 1", name="chk_order_items_discount_range"),
        Index("idx_order_items_order_id", "order_id"),
        Index("idx_order_items_product_id", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.order_item_id}, order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"


class Payment(Base):
    """Represents a payment transaction for an order."""
    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(NUMERIC(12, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="payments")

    # Constraints & Indexes
    __table_args__ = (
        CheckConstraint(
            "payment_method IN ('Credit Card', 'Debit Card', 'PayPal', 'Bank Transfer', 'Cash', 'UPI', 'Crypto')",
            name="chk_payments_method"
        ),
        CheckConstraint(
            "payment_status IN ('Pending', 'Completed', 'Failed', 'Refunded')",
            name="chk_payments_status"
        ),
        CheckConstraint("amount >= 0", name="chk_payments_amount_nonnegative"),
        Index("idx_payments_order_id", "order_id"),
        Index("idx_payments_payment_date", "payment_date"),
        Index("idx_payments_status", "payment_status"),
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.payment_id}, order_id={self.order_id}, amount={self.amount}, status='{self.payment_status}')>"


class Review(Base):
    """Represents a customer review for a product."""
    __tablename__ = "reviews"

    review_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[Optional[str]] = mapped_column(Text)
    review_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="reviews")
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")

    # Constraints & Indexes
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="chk_reviews_rating_range"),
        Index("idx_reviews_customer_id", "customer_id"),
        Index("idx_reviews_product_id", "product_id"),
        Index("idx_reviews_rating", "rating"),
        Index("idx_reviews_date", "review_date"),
    )

    def __repr__(self) -> str:
        return f"<Review(id={self.review_id}, rating={self.rating}, product_id={self.product_id})>"


# ── Schema Management Functions ─────────────────────────────────────────────

def create_tables():
    """Creates all tables in the database."""
    print("Creating all tables using SQLAlchemy ORM...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")
    list_tables()


def drop_all_tables():
    """Drops all tables. Use with caution — this deletes all data!"""
    confirm = input("Are you sure you want to drop ALL tables? (yes/no): ")
    if confirm.lower() == "yes":
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped.")
    else:
        print("Drop cancelled.")


def list_tables():
    """Lists all tables currently in the database."""
    # pyrefly: ignore [missing-import]
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("\nTables in database:")
    for table in tables:
        print(f"  - {table}")
    return tables


def get_table_schema(table_name: str):
    """Prints the column details for a given table."""
    # pyrefly: ignore [missing-import]
    from sqlalchemy import inspect
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    print(f"\n📋 {table_name.upper()}")
    print("-" * 60)
    for col in columns:
        default = f" [DEFAULT: {col['default']}]" if col.get("default") else ""
        nullable = "NULL" if col["nullable"] else "NOT NULL"
        print(f"  {col['name']:<20} {str(col['type']):<20} {nullable}{default}")


def get_db_session():
    """Returns a new database session. Use with 'with' statement."""
    return SessionLocal()


# ── Main Entry Point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 1. Create all tables
    create_tables()

    # 2. (Optional) Print schema details for each table
    print("\n" + "=" * 60)
    print("SCHEMA DETAILS")
    print("=" * 60)
    for table_name in ["customers", "products", "orders", "order_items", "payments", "reviews"]:
        get_table_schema(table_name)

    # 3. (Optional) Drop all tables — uncomment only if you need to reset
    # drop_all_tables()