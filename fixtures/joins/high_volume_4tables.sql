SELECT o.order_id, c.name, p.title, s.region
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items i ON o.order_id = i.order_id
JOIN products p ON i.product_id = p.product_id
JOIN stores s ON o.store_id = s.store_id
WHERE o.order_date >= '2024-01-01'
