
USE PharmacyDB;
GO

CREATE OR ALTER VIEW clean.vw_pharmacy_sales_enriched AS
SELECT
    s.*,

    -- 1. Gross sales before discount
    CAST(
        s.Quantity * s.Unit_Price_LKR
        AS DECIMAL(18,2)
    ) AS Gross_Sales_LKR,

    -- 2. Discount amount
    CAST(
        s.Quantity * s.Unit_Price_LKR * s.Discount_Rate
        AS DECIMAL(18,2)
    ) AS Discount_Amount_LKR,

    -- 3. Net sales after discount
    CAST(
        s.Quantity * s.Unit_Price_LKR *
        (1 - s.Discount_Rate)
        AS DECIMAL(18,2)
    ) AS Calculated_Net_Sales_LKR,

    -- 4. Days remaining until expiry at sale
    DATEDIFF(
        DAY,
        s.Transaction_Date,
        s.Expiry_Date
    ) AS Days_To_Expiry

FROM clean.vw_pharmacy_sales AS s;
GO






