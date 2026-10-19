-- query joining two large tables without join predicate (cartesian risk)
SELECT o.order_id, c.customer_name, SUM(o.amount) AS total
FROM orders o
JOIN customers c
WHERE o.order_date >= '2026-01-01'
GROUP BY o.order_id, c.customer_name
ORDER BY total DESC;
