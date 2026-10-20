SELECT a.id, b.id
FROM events a
JOIN windows b ON a.ts BETWEEN b.start_ts AND b.end_ts
