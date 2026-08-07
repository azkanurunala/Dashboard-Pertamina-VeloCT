-- verify_daily_scraping.sql -- prove daily scraping ran, per topic.
-- Run: psql "$NEON_DB_URL" -f scripts/verify_daily_scraping.sql
-- Or paste into any Postgres client connected to Neon.

-- ALL news topics (raw scraping runs daily for every topic, regardless of
-- how often that topic's summary gets aggregated -- see ACTIVE_SHEETS in
-- main_news_scraping_lokal.py / main_news_scraping_internasional.py)
SELECT
    topic,
    MAX(date)                    AS latest_date,
    CURRENT_DATE - MAX(date)     AS days_stale,
    COUNT(*) FILTER (WHERE date = CURRENT_DATE - 1) AS rows_yesterday
FROM news_articles
GROUP BY topic
ORDER BY latest_date;

-- Daily summary topics (Gemini daily summaries)
SELECT
    topic,
    MAX("Tanggal akhir")                    AS latest_date,
    CURRENT_DATE - MAX("Tanggal akhir")     AS days_stale,
    COUNT(*) FILTER (WHERE "Tanggal akhir" = CURRENT_DATE - 1) AS rows_yesterday
FROM news_sentiment
WHERE topic IN ('(Summary)Nilai Tukar Rupiah', '(Summary)IHSG', '(Summary)Indonia', '(Summary)Idx Volatilitas', '(Summary)Idx Risiko Geopolitik')
GROUP BY topic
ORDER BY latest_date;

-- Exact check for one target date, ALL topics (edit the date below)
SELECT topic, COUNT(*) AS rows_found
FROM news_articles
WHERE date = DATE '2026-08-05'
GROUP BY topic
ORDER BY topic;

SELECT topic, COUNT(*) AS rows_found
FROM news_sentiment
WHERE "Tanggal akhir" = DATE '2026-08-05'
  AND topic IN ('(Summary)Nilai Tukar Rupiah', '(Summary)IHSG', '(Summary)Indonia', '(Summary)Idx Volatilitas', '(Summary)Idx Risiko Geopolitik')
GROUP BY topic;
