"""
Week 1, Day 1-2: Python Refresher
Practice: functions, classes, decorators, type hints
"""

# ============================================
# FUNCTIONS AND TYPE HINTS
# ============================================

from typing import List, Dict, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime


def calculate_discount(price: float, discount_percent: float) -> float:
    """Calculate discounted price with type hints."""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)


def process_orders(
    orders: List[Dict[str, Union[str, float]]],
    status_filter: Optional[str] = None
) -> List[Dict[str, Union[str, float]]]:
    """Process orders with optional filtering."""
    if status_filter:
        return [order for order in orders if order.get("status") == status_filter]
    return orders


# ============================================
# CLASSES
# ============================================

class Customer:
    """Basic customer class."""
    
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        self._orders: List[Dict] = []
    
    def add_order(self, order: Dict) -> None:
        """Add an order to the customer."""
        self._orders.append(order)
    
    def get_total_spent(self) -> float:
        """Calculate total spent across all orders."""
        return sum(order.get("total", 0) for order in self._orders)
    
    def __repr__(self) -> str:
        return f"Customer(name={self.name}, email={self.email})"


@dataclass
class Order:
    """Order dataclass for cleaner code."""
    id: int
    customer_id: int
    product_name: str
    status: str
    total: float
    created_at: datetime = datetime.now()


# ============================================
# DECORATORS
# ============================================

def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    import time
    
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper


def logging_decorator(func: Callable) -> Callable:
    """Decorator to log function calls."""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper


def retry_decorator(max_retries: int = 3, delay: float = 1.0):
    """Decorator with parameters for retrying failed operations."""
    import time
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


# ============================================
# PRACTICE EXERCISES
# ============================================

@timing_decorator
@logging_decorator
def expensive_computation(n: int) -> int:
    """Simulate an expensive computation."""
    import time
    time.sleep(0.1)  # Simulate work
    return sum(range(n))


@retry_decorator(max_retries=3, delay=0.5)
def unreliable_function(success_rate: float = 0.5) -> str:
    """Function that fails randomly for testing retry decorator."""
    import random
    if random.random() < success_rate:
        return "Success!"
    raise ValueError("Random failure occurred")


# ============================================
# TEST THE CODE
# ============================================

if __name__ == "__main__":
    print("=== Functions and Type Hints ===")
    discounted = calculate_discount(100.0, 15.0)
    print(f"Discounted price: ${discounted:.2f}")
    
    orders = [
        {"id": 1, "status": "completed", "total": 50.0},
        {"id": 2, "status": "pending", "total": 30.0},
        {"id": 3, "status": "completed", "total": 70.0},
    ]
    
    completed_orders = process_orders(orders, status_filter="completed")
    print(f"Completed orders: {len(completed_orders)}")
    
    print("\n=== Classes ===")
    customer = Customer("John Doe", "john@example.com")
    customer.add_order({"id": 1, "total": 50.0})
    customer.add_order({"id": 2, "total": 30.0})
    print(f"{customer}")
    print(f"Total spent: ${customer.get_total_spent():.2f}")
    
    order = Order(id=1, customer_id=1, product_name="Widget", status="pending", total=99.99)
    print(f"Order: {order}")
    
    print("\n=== Decorators ===")
    result = expensive_computation(1000)
    print(f"Result: {result}")
    
    print("\n=== Retry Decorator ===")
    try:
        result = unreliable_function(success_rate=0.3)
        print(f"Final result: {result}")
    except Exception as e:
        print(f"All retries failed: {e}")
    
    print("\n[SUCCESS] All exercises completed!")
