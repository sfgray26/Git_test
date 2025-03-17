DECLARE @sql NVARCHAR(MAX);
DECLARE @unionSql NVARCHAR(MAX);

SET @sql = '';
SET @unionSql = '';

-- Build dynamic SQL for each matching table and column
SELECT @sql = @sql +
    'SELECT ''' + C1.TABLE_SCHEMA + '.' + C1.TABLE_NAME + ''' AS TableName, ' +
    'CAST(' + QUOTENAME(C2.COLUMN_NAME) + ' AS DATE) AS Date, ' +
    'COUNT(*) AS Volume ' +
    'FROM ' + QUOTENAME(C1.TABLE_SCHEMA) + '.' + QUOTENAME(C1.TABLE_NAME) + ' ' +
    'WHERE ' + QUOTENAME(C1.COLUMN_NAME) + ' IS NOT NULL ' +
    'GROUP BY CAST(' + QUOTENAME(C2.COLUMN_NAME) + ' AS DATE); ' +
    '-- UNION ALL will be added later' + CHAR(13) + CHAR(10)
FROM INFORMATION_SCHEMA.COLUMNS C1
JOIN INFORMATION_SCHEMA.COLUMNS C2
    ON C1.TABLE_NAME = C2.TABLE_NAME
    AND C1.TABLE_SCHEMA = C2.TABLE_SCHEMA
WHERE (C1.COLUMN_NAME LIKE '%comment%' OR C1.COLUMN_NAME LIKE '%remark%' OR C1.COLUMN_NAME LIKE '%feedback%')
    AND (C2.COLUMN_NAME LIKE '%date%' OR C2.COLUMN_NAME LIKE '%time%')
    AND C2.DATA_TYPE IN ('date', 'datetime', 'smalldatetime', 'timestamp');

-- Remove trailing newline characters
IF LEN(@sql) > 0
BEGIN
    SET @sql = LEFT(@sql, LEN(@sql) - 2); -- Remove last newline
END

-- Build UNION ALL string
IF LEN(@sql) > 0
BEGIN
    SET @unionSql = REPLACE(@sql, '-- UNION ALL will be added later' + CHAR(13) + CHAR(10), 'UNION ALL' + CHAR(13) + CHAR(10));
    SET @unionSql = LEFT(@unionSql, LEN(@unionSql) - 11); -- Remove last UNION ALL and line break
END

-- Execute dynamic SQL
IF LEN(@unionSql) > 0
BEGIN
    PRINT @unionSql;
    EXEC sp_executesql @unionSql;
END
ELSE
BEGIN
    PRINT 'No valid tables or columns found to search';
END;
