SELECT o.id, c.name, i.qty
FROM orders o
JOIN customers c ON o.cid = c.id
JOIN order_items i ON o.id = i.oid
JOIN products p ON i.pid = p.id
WHERE o.dt >= '2024-01-01'
