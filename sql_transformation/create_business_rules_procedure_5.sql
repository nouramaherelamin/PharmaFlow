
USE PharmacyDB;
GO

CREATE OR ALTER PROCEDURE clean.usp_validate_business_rules
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @TotalRows INT;
    DECLARE @InvalidRows INT;
    DECLARE @DuplicateTransactions INT;
    DECLARE @InvalidYearMonth INT;

    SELECT
        @TotalRows = COUNT(*),

        @InvalidRows = COALESCE(SUM(CASE
            WHEN TRY_CONVERT(INT, Quantity) <= 0
              OR TRY_CONVERT(DECIMAL(18,2), Unit_Price_LKR) < 0
              OR TRY_CONVERT(DECIMAL(9,4), Discount_Rate)
                    NOT BETWEEN 0 AND 1
              OR TRY_CONVERT(DATE, Expiry_Date, 101)
                    < TRY_CONVERT(DATE, Transaction_Date, 101)
            THEN 1 ELSE 0
        END), 0),

        @DuplicateTransactions =
            COUNT(*) - COUNT(DISTINCT Transaction_ID),

        @InvalidYearMonth = COALESCE(SUM(CASE
            WHEN TRY_CONVERT(INT, [Year]) <>
                 YEAR(TRY_CONVERT(DATE, Transaction_Date, 101))
              OR TRY_CONVERT(INT, [Month]) <>
                 MONTH(TRY_CONVERT(DATE, Transaction_Date, 101))
            THEN 1 ELSE 0
        END), 0)

    FROM stg.pharmacy_raw;

    SELECT
        @TotalRows AS Total_Rows,
        @InvalidRows AS Invalid_Business_Rule_Rows,
        @DuplicateTransactions AS Duplicate_Transactions,
        @InvalidYearMonth AS Invalid_Year_Month;

    IF @TotalRows = 0
       OR @InvalidRows > 0
       OR @DuplicateTransactions > 0
       OR @InvalidYearMonth > 0
    BEGIN
        THROW 50002,
            'Business Rules Validation Failed',
            1;
    END;

    PRINT 'Business Rules Validation Passed';
END;
GO
