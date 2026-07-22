"""
Week 1, Day 1-2: Python Refresher
Learn pydantic for data validation (BaseModel, Field, validators)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum


# ============================================
# BASIC PYDANTIC MODEL
# ============================================

class Customer(BaseModel):
    """Basic customer model with validation."""
    name: str
    email: str
    age: int = Field(default=0, ge=0, le=120, description="Customer age")
    
    @field_validator('email')
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        """Validate email format."""
        if '@' not in v:
            raise ValueError('Email must contain @')
        return v.lower()
    
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


# ============================================
# COMPLEX MODEL WITH NESTING
# ============================================

class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """Individual item in an order."""
    product_id: str = Field(..., min_length=1, description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity must be positive")
    price: float = Field(..., gt=0, description="Price must be positive")
    
    @property
    def total(self) -> float:
        """Calculate line item total."""
        return self.quantity * self.price


class Order(BaseModel):
    """Complete order model."""
    id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    customer_id: str
    items: List[OrderItem] = Field(default_factory=list, min_length=1)
    status: OrderStatus = OrderStatus.PENDING
    total: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('items')
    @classmethod
    def items_must_not_be_empty(cls, v: List[OrderItem]) -> List[OrderItem]:
        """Validate order has at least one item."""
        if not v:
            raise ValueError('Order must have at least one item')
        return v
    
    @field_validator('total')
    @classmethod
    def calculate_total(cls, v: float, info) -> float:
        """Calculate total from items if not provided."""
        # If total is 0, calculate from items
        if v == 0.0 and 'items' in info.data:
            items = info.data['items']
            return sum(item.total for item in items)
        return v
    
    def add_item(self, item: OrderItem) -> None:
        """Add an item to the order."""
        self.items.append(item)
        self.total = sum(item.total for item in self.items)


# ============================================
# ADVANCED VALIDATION
# ============================================

class SupportTicket(BaseModel):
    """Support ticket with complex validation."""
    customer_id: str
    subject: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    order_id: Optional[str] = None
    status: str = "open"
    created_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('order_id')
    @classmethod
    def order_id_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate order ID format if provided."""
        if v is not None and not v.startswith("ORD-"):
            raise ValueError('Order ID must start with "ORD-"')
        return v
    
    @field_validator('priority')
    @classmethod
    def priority_validation(cls, v: str) -> str:
        """Ensure priority is lowercase."""
        return v.lower()


# ============================================
# CONFIG AND SETTINGS
# ============================================

class DatabaseConfig(BaseModel):
    """Database configuration."""
    model_config = ConfigDict(extra='forbid')
    
    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    username: str
    password: str
    database: str
    pool_size: int = Field(default=10, ge=1, le=100)


class AppConfig(BaseModel):
    """Application configuration."""
    app_name: str = "Dispatch AI"
    debug: bool = False
    database: DatabaseConfig
    api_keys: List[str] = Field(default_factory=list)
    
    @field_validator('api_keys')
    @classmethod
    def api_keys_must_not_be_empty(cls, v: List[str]) -> List[str]:
        """Validate API keys if debug is False."""
        # This is a simplified check - in real app, you'd check the actual config
        return v


# ============================================
# DEMONSTRATIONS
# ============================================

def demo_basic_validation():
    """Demonstrate basic Pydantic validation."""
    print("=== Basic Validation ===")
    
    # Valid customer
    customer = Customer(name="John Doe", email="john@example.com", age=30)
    print(f"Valid customer: {customer}")
    print(f"Email (lowercased): {customer.email}")
    
    # Invalid email (will raise error)
    try:
        invalid_customer = Customer(name="Jane", email="invalid-email", age=25)
    except ValueError as e:
        print(f"Validation error: {e}")
    
    # Invalid name (will raise error)
    try:
        invalid_customer = Customer(name="   ", email="jane@example.com", age=25)
    except ValueError as e:
        print(f"Validation error: {e}")


def demo_complex_model():
    """Demonstrate complex nested model."""
    print("\n=== Complex Model ===")
    
    # Create order with items
    order = Order(
        customer_id="CUST-001",
        items=[
            OrderItem(product_id="PROD-001", quantity=2, price=29.99),
            OrderItem(product_id="PROD-002", quantity=1, price=49.99),
        ],
        status=OrderStatus.PENDING
    )
    
    print(f"Order ID: {order.id}")
    print(f"Customer ID: {order.customer_id}")
    print(f"Status: {order.status}")
    print(f"Items: {len(order.items)}")
    print(f"Total: ${order.total:.2f}")
    
    # Add another item
    order.add_item(OrderItem(product_id="PROD-003", quantity=3, price=9.99))
    print(f"Total after adding item: ${order.total:.2f}")
    
    # Invalid order (no items)
    try:
        invalid_order = Order(customer_id="CUST-002", items=[])
    except ValueError as e:
        print(f"Validation error: {e}")


def demo_support_ticket():
    """Demonstrate support ticket validation."""
    print("\n=== Support Ticket ===")
    
    # Valid ticket
    ticket = SupportTicket(
        customer_id="CUST-001",
        subject="Order not received",
        description="I ordered a widget last week but haven't received it yet.",
        priority="high",
        order_id="ORD-12345"
    )
    print(f"Valid ticket: {ticket.subject}")
    print(f"Priority: {ticket.priority}")
    
    # Invalid order ID format
    try:
        invalid_ticket = SupportTicket(
            customer_id="CUST-002",
            subject="Question",
            description="I have a question about my order.",
            order_id="12345"  # Missing "ORD-" prefix
        )
    except ValueError as e:
        print(f"Validation error: {e}")


def demo_config():
    """Demonstrate configuration validation."""
    print("\n=== Configuration ===")
    
    config = AppConfig(
        debug=True,
        database=DatabaseConfig(
            host="localhost",
            port=5432,
            username="admin",
            password="secret",
            database="dispatch_ai"
        )
    )
    
    print(f"App: {config.app_name}")
    print(f"Debug: {config.debug}")
    print(f"Database: {config.database.host}:{config.database.port}")
    print(f"Database: {config.database.database}")


def demo_json_serialization():
    """Demonstrate JSON serialization."""
    print("\n=== JSON Serialization ===")
    
    customer = Customer(name="Alice", email="alice@example.com", age=28)
    
    # Convert to JSON
    customer_json = customer.model_dump_json()
    print(f"JSON: {customer_json}")
    
    # Convert from JSON
    customer_dict = customer.model_dump()
    print(f"Dict: {customer_dict}")
    
    # Parse from dict
    customer_copy = Customer(**customer_dict)
    print(f"Copy: {customer_copy}")


def demo_schema():
    """Demonstrate JSON schema generation."""
    print("\n=== JSON Schema ===")
    
    schema = Order.model_json_schema()
    print(f"Order schema keys: {list(schema.keys())}")
    print(f"Required fields: {schema.get('required', [])}")


# ============================================
# MAIN DEMO
# ============================================

if __name__ == "__main__":
    print("[Pydantic Validation Exercises]\n")
    
    demo_basic_validation()
    demo_complex_model()
    demo_support_ticket()
    demo_config()
    demo_json_serialization()
    demo_schema()
    
    print("\n[SUCCESS] All Pydantic exercises completed!")
    print("\n[Next steps]")
    print("   - Install pydantic: pip install pydantic")
    print("   - Run this file: python experiments/03_pydantic_validation.py")
    print("   - Try creating your own models for the Dispatch AI project")
