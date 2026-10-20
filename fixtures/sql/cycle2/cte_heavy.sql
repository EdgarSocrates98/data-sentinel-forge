WITH a AS (SELECT id, x FROM t1),
     b AS (SELECT id, y FROM a JOIN t2 ON a.id = t2.id),
     c AS (SELECT id, z FROM b JOIN t3 ON b.id = t3.id),
     d AS (SELECT id, w FROM c JOIN t4 ON c.id = t4.id)
SELECT * FROM d
