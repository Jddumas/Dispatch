-- Practice queries for the Otto support database

-- 1. List all customers with their total number of orders.
SELECT c.id, c.name, COUNT(o.id) AS order_count
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY order_count DESC;

-- 2. Find all open orders for a specific customer (id = 1).
SELECT *
FROM orders
WHERE customer_id = 1 AND status = 'pending';

-- 3. Get total revenue by month.
SELECT DATE_TRUNC('month', created_at) AS month, SUM(total) AS revenue
FROM orders
GROUP BY month
ORDER BY month;

-- 4. List unresolved support tickets with customer and order details.
SELECT t.id, t.subject, t.status, c.name AS customer_name, o.product_name
FROM support_tickets t
JOIN customers c ON t.customer_id = c.id
JOIN orders o ON t.order_id = o.id
WHERE t.status != 'resolved';

-- 5. Top 5 customers by total spend.
SELECT c.id, c.name, SUM(o.total) AS total_spend
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY total_spend DESC
LIMIT 5;

-- 6. Count orders by status.
SELECT status, COUNT(*) AS count
FROM orders
GROUP BY status;

-- 7. Orders placed in the last 30 days.
SELECT *
FROM orders
WHERE created_at >= NOW() - INTERVAL '30 days';

-- 8. Support tickets created in the last 7 days.
SELECT t.*, c.name AS customer_name
FROM support_tickets t
JOIN customers c ON t.customer_id = c.id
WHERE t.created_at >= NOW() - INTERVAL '7 days';

-- 9. Average order value.
SELECT AVG(total) AS average_order_value
FROM orders;

-- 10. Customers who have not placed any orders.
SELECT c.id, c.name
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.id IS NULL;
