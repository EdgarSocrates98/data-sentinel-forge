WITH ranked AS (
  SELECT order_id, customer_id, amount,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rn
  FROM orders
)
SELECT order_id, customer_id, amount
FROM ranked
WHERE rn = 1
LIMIT 100;
