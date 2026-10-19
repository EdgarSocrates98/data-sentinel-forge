SELECT o.order_id, c.customer_name, o.amount
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.order_date >= DATE '2026-01-01'
ORDER BY o.amount DESC
LIMIT 100;
