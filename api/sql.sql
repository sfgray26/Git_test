DECLARE @sql NVARCHAR(MAX) = '';

-- Build dynamic SQL for each matching table and column
SELECT @sql += 
    'SELECT ''' + TABLE_SCHEMA + '.' + TABLE_NAME + ''' AS TableName, ' +
    'CAST(' + QUOTENAME(COLUMN_NAME) + ' AS DATE) AS Date, COUNT(*) AS Volume ' +
    'FROM ' + QUOTENAME(TABLE_SCHEMA) + '.' + QUOTENAME(TABLE_NAME) +
    ' WHERE ' + QUOTENAME(COLUMN_NAME) + ' IS NOT NULL ' +
    'GROUP BY CAST(' + QUOTENAME(COLUMN_NAME) + ' AS DATE) UNION ALL '
FROM INFORMATION_SCHEMA.COLUMNS
WHERE 
    (COLUMN_NAME LIKE '%comment%' OR COLUMN_NAME LIKE '%remark%' OR COLUMN_NAME LIKE '%feedback%')
    AND EXISTS (
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS AS C2
        WHERE C2.TABLE_NAME = INFORMATION_SCHEMA.COLUMNS.TABLE_NAME 
        AND C2.TABLE_SCHEMA = INFORMATION_SCHEMA.COLUMNS.TABLE_SCHEMA
        AND (C2.COLUMN_NAME LIKE '%date%' OR C2.COLUMN_NAME LIKE '%time%')
        -- ✅ Only select valid date types
        AND C2.DATA_TYPE IN ('date', 'datetime', 'smalldatetime', 'timestamp')
    );

-- Remove trailing UNION ALL
IF LEN(@sql) > 0
    SET @sql = LEFT(@sql, LEN(@sql) - 10);

-- Print and execute the query
PRINT @sql;
EXEC sp_executesql @sql;