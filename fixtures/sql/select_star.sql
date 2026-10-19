-- wide SELECT * with non-sargable predicate
SELECT *
FROM fact_events e
WHERE CAST(e.event_ts AS DATE) = '2026-10-01'
  AND UPPER(e.region) = 'US-EAST';
