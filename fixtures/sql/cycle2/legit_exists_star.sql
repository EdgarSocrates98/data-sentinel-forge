SELECT o.id FROM orders o
WHERE EXISTS (SELECT * FROM items i WHERE i.oid = o.id)
