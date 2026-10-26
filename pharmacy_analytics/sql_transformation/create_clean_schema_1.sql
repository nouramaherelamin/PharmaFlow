
USE PharmacyDB;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'clean'
)
BEGIN
    EXEC('CREATE SCHEMA clean');
END;
GO
