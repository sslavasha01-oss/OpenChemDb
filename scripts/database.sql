--узнать размер всех индексов
SELECT
    pg_size_pretty(SUM(pg_relation_size(indexrelid))) AS "Общий вес всех индексов",
    (SUM(pg_relation_size(indexrelid)) / 1024 / 1024) AS "Вес в МБ (число)"
FROM pg_stat_user_indexes;

--прогрев всех индексов для фулл рам режима
DO $$
DECLARE
    idx_name RECORD;
BEGIN
    FOR idx_name IN
        SELECT indexrelid::regclass AS name
        FROM pg_index
        JOIN pg_class c ON c.oid = pg_index.indrelid
        WHERE c.relkind = 'r' -- только для обычных таблиц
    LOOP
        RAISE NOTICE 'Прогреваю индекс: %', idx_name.name;
        PERFORM pg_prewarm(idx_name.name);
    END LOOP;
END $$;

--узнать размер индексов в оперативной памяти
SELECT
    c.relname AS index_name,
    t.relname AS table_name,
    count(*) * 8 / 1024 AS size_in_ram_mb,
    pg_size_pretty(pg_relation_size(c.oid)) AS total_index_size,
    round(100.0 * count(*) / (pg_relation_size(c.oid) / (current_setting('block_size')::int8)), 2) AS percent_in_ram
FROM
    pg_buffercache b
INNER JOIN
    pg_class c ON b.relfilenode = pg_relation_filenode(c.oid) AND b.reldatabase IN (0, (SELECT oid FROM pg_database WHERE datname = current_database()))
INNER JOIN
    pg_index i ON c.oid = i.indexrelid
INNER JOIN
    pg_class t ON i.indrelid = t.oid
WHERE
    c.relkind = 'i'
GROUP BY
    c.oid, c.relname, t.relname
ORDER BY
    size_in_ram_mb DESC;