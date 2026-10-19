SELECT a.id, b.name
FROM orders a, customers b
WHERE a.customer_id = b.id;
