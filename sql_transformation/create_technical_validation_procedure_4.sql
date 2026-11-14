
USE PharmacyDB;
GO

CREATE OR ALTER PROCEDURE clean.usp_validate_technical
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @TotalRows INT;
    DECLARE @InvalidRows INT;
    DECLARE @MissingStrength INT;
    DECLARE @InvalidStrength INT;

    SELECT
        @TotalRows = COUNT(*),

        -- Validate all required numeric and date fields
        @InvalidRows = COALESCE(SUM(CASE
            WHEN TRY_CONVERT(INT,
                     NULLIF(TRIM(Transaction_ID), '')) IS NULL

              OR TRY_CONVERT(DATE,
                     NULLIF(TRIM(Transaction_Date), ''), 101) IS NULL

              OR TRY_CONVERT(INT,
                     NULLIF(TRIM(Branch_ID), '')) IS NULL

              OR TRY_CONVERT(INT,
                     NULLIF(TRIM(Medicine_ID), '')) IS NULL

              OR TRY_CONVERT(INT,
                     NULLIF(TRIM(Customer_Age), '')) IS NULL

              OR TRY_CONVERT(DATE,
                     NULLIF(TRIM(Expiry_Date), ''), 101) IS NULL

              OR TRY_CONVERT(INT,
                     NULLIF(TRIM(Quantity), '')) IS NULL

              OR TRY_CONVERT(DECIMAL(18,2),
                     NULLIF(TRIM(Unit_Price_LKR), '')) IS NULL

              OR TRY_CONVERT(DECIMAL(9,4),
                     NULLIF(TRIM(Discount_Rate), '')) IS NULL

              OR TRY_CONVERT(DECIMAL(18,2),
                     NULLIF(TRIM(Line_Total_LKR), '')) IS NULL

              OR TRY_CONVERT(INT,
                     NULLIF(TRIM([Year]), '')) IS NULL

              OR TRY_CONVERT(INT,
                     NULLIF(TRIM([Month]), '')) IS NULL

            THEN 1 ELSE 0
        END), 0),

        -- Missing strength is allowed
        @MissingStrength = COALESCE(SUM(CASE
            WHEN NULLIF(TRIM(Strength_mg), '') IS NULL
            THEN 1 ELSE 0
        END), 0),

        -- Non-empty strength must be numeric
        @InvalidStrength = COALESCE(SUM(CASE
            WHEN NULLIF(TRIM(Strength_mg), '') IS NOT NULL
             AND TRY_CONVERT(
                 DECIMAL(18,2),
                 NULLIF(TRIM(Strength_mg), '')
             ) IS NULL
            THEN 1 ELSE 0
        END), 0)

    FROM stg.pharmacy_raw;

    -- Display validation results
    SELECT
        @TotalRows AS Total_Rows,
        @InvalidRows AS Invalid_Rows,
        @MissingStrength AS Missing_Strength,
        @InvalidStrength AS Invalid_Strength;

    -- Stop the pipeline on invalid data
    IF @TotalRows = 0
       OR @InvalidRows > 0
       OR @InvalidStrength > 0
    BEGIN
        THROW 50001,
            'Technical Data Quality Validation Failed',
            1;
    END;

    PRINT 'Technical Data Quality Validation Passed';
END;
GO

