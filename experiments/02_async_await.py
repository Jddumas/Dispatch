"""
Week 1, Day 1-2: Python Refresher
Practice: async/await with asyncio and httpx
"""

import asyncio
import time
from typing import List, Dict


# ============================================
# BASIC ASYNC CONCEPTS
# ============================================

async def say_hello(name: str, delay: float = 1.0) -> str:
    """Simple async function with delay."""
    print(f"Starting hello for {name}...")
    await asyncio.sleep(delay)  # Simulate I/O operation
    print(f"Finished hello for {name}!")
    return f"Hello, {name}!"


async def main_basic() -> None:
    """Basic async main function."""
    print("=== Basic Async ===")
    result = await say_hello("World", 0.5)
    print(result)


# ============================================
# CONCURRENT EXECUTION
# ============================================

async def fetch_data(url: str, delay: float) -> Dict[str, str]:
    """Simulate fetching data from an API."""
    print(f"Fetching from {url}...")
    await asyncio.sleep(delay)
    return {"url": url, "data": f"Data from {url}"}


async def fetch_multiple_urls() -> List[Dict[str, str]]:
    """Fetch multiple URLs concurrently."""
    urls = [
        ("https://api.example.com/users", 1.0),
        ("https://api.example.com/products", 0.8),
        ("https://api.example.com/orders", 1.2),
    ]
    
    # Create tasks for concurrent execution
    tasks = [fetch_data(url, delay) for url, delay in urls]
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    return results


# ============================================
# ASYNC CONTEXT MANAGERS
# ============================================

class AsyncTimer:
    """Async context manager for timing operations."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        print(f"{self.name}: Starting...")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        print(f"{self.name}: Finished in {elapsed:.2f}s")
        return False


async def demo_context_manager() -> None:
    """Demonstrate async context manager."""
    async with AsyncTimer("Data Processing"):
        await asyncio.sleep(1.0)
        # Simulate processing
        await asyncio.sleep(0.5)


# ============================================
# HTTPX FOR ASYNC HTTP REQUESTS
# ============================================

# Note: Uncomment this section when you have httpx installed
# Run: pip install httpx

async def fetch_with_httpx(url: str) -> str:
    """Fetch data using httpx (async HTTP client)."""
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text


async def demo_httpx() -> None:
    """Demonstrate httpx for async HTTP requests."""
    try:
        # Using a public API for testing
        url = "https://jsonplaceholder.typicode.com/posts/1"
        data = await fetch_with_httpx(url)
        print(f"Fetched data: {data[:100]}...")
    except Exception as e:
        print(f"HTTPX demo failed (install httpx first): {e}")


# ============================================
# PRACTICAL EXAMPLE: API RATE LIMITING
# ============================================

class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 2.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = None
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        if self.last_call is not None:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


async def fetch_with_rate_limit(url: str, limiter: RateLimiter) -> Dict:
    """Fetch URL with rate limiting."""
    await limiter.wait_if_needed()
    print(f"Fetching {url}...")
    await asyncio.sleep(0.5)  # Simulate API call
    return {"url": url, "status": "success"}


async def demo_rate_limiting() -> None:
    """Demonstrate rate limiting."""
    print("\n=== Rate Limiting Demo ===")
    limiter = RateLimiter(calls_per_second=2.0)
    
    urls = [f"https://api.example.com/endpoint/{i}" for i in range(5)]
    
    start = time.time()
    tasks = [fetch_with_rate_limit(url, limiter) for url in urls]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    print(f"Fetched {len(results)} URLs in {elapsed:.2f}s")
    print(f"Expected minimum time: {len(urls) / 2.0:.2f}s (2 calls/sec)")


# ============================================
# ERROR HANDLING IN ASYNC
# ============================================

async def faulty_operation(should_fail: bool) -> str:
    """Operation that may fail."""
    await asyncio.sleep(0.5)
    if should_fail:
        raise ValueError("Operation failed!")
    return "Success!"


async def demo_error_handling() -> None:
    """Demonstrate async error handling."""
    print("\n=== Error Handling Demo ===")
    
    # Try-except in async
    try:
        result = await faulty_operation(should_fail=True)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Caught error: {e}")
    
    # Handle errors in gather
    tasks = [
        faulty_operation(should_fail=False),
        faulty_operation(should_fail=True),
        faulty_operation(should_fail=False),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task {i} failed: {result}")
        else:
            print(f"Task {i} succeeded: {result}")


# ============================================
# MAIN DEMO
# ============================================

async def main() -> None:
    """Run all demonstrations."""
    await main_basic()
    
    print("\n=== Concurrent Fetching ===")
    results = await fetch_multiple_urls()
    for result in results:
        print(f"  - {result['url']}: {result['data']}")
    
    await demo_context_manager()
    
    # Uncomment to test httpx (requires installation)
    # await demo_httpx()
    
    await demo_rate_limiting()
    await demo_error_handling()
    
    print("\n[SUCCESS] All async exercises completed!")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
