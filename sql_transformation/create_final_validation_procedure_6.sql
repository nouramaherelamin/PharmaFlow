
USE PharmacyDB;
GO

CREATE OR ALTER PROCEDURE clean.usp_validate_final
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RawRows BIGINT;
    DECLARE @FinalRows BIGINT;
    DECLARE @UniqueTransactions BIGINT;
    DECLARE @MissingRequired BIGINT;
    DECLARE @SalesMismatches BIGINT;
    DECLARE @MaxSalesDifference DECIMAL(18,2);

    SELECT @RawRows = COUNT_BIG(*)
    FROM stg.pharmacy_raw;

    SELECT
        @FinalRows = COUNT_BIG(*),
        @UniqueTransactions =
            COUNT_BIG(DISTINCT Transaction_ID),

        @MissingRequired = COALESCE(SUM(CASE
            WHEN Transaction_ID IS NULL
              OR Transaction_Date IS NULL
              OR Medicine_ID IS NULL
              OR Branch_ID IS NULL
              OR Quantity IS NULL
              OR Unit_Price_LKR IS NULL
              OR Discount_Rate IS NULL
              OR Line_Total_LKR IS NULL
            THEN 1 ELSE 0
        END), 0),

        @SalesMismatches = COALESCE(SUM(CASE
            WHEN Calculated_Net_Sales_LKR IS NULL
              OR ABS(
                  Line_Total_LKR -
                  Calculated_Net_Sales_LKR
              ) > 0.01
            THEN 1 ELSE 0
        END), 0),

        @MaxSalesDifference =
            MAX(ABS(
                Line_Total_LKR -
                Calculated_Net_Sales_LKR
            ))

    FROM clean.vw_pharmacy_sales_enriched;

    SELECT
        @RawRows AS Raw_Rows,
        @FinalRows AS Final_Rows,
        @UniqueTransactions AS Unique_Transactions,
        @MissingRequired AS Missing_Required,
        @SalesMismatches AS Sales_Mismatches,
        @MaxSalesDifference AS Max_Sales_Difference;

    IF @RawRows = 0
       OR @RawRows <> @FinalRows
       OR @FinalRows <> @UniqueTransactions
       OR @MissingRequired > 0
       OR @SalesMismatches > 0
    BEGIN
        THROW 50003,
            'Final Transformation Validation Failed',
            1;
    END;
END;
GO


