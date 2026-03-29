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