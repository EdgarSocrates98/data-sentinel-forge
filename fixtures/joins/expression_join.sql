SELECT a.id
FROM t1 a
JOIN t2 b ON lower(a.name) = lower(b.name)
