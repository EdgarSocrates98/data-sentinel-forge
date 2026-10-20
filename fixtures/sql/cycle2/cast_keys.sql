SELECT a.id FROM t1 a
JOIN t2 b ON CAST(a.k AS STRING) = b.k
