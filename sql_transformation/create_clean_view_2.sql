USE PharmacyDB;
GO
CREATE OR ALTER VIEW clean.vw_pharmacy_sales AS
SELECT
    TRY_CONVERT(INT, Transaction_ID) AS Transaction_ID,
    TRY_CONVERT(DATE, Transaction_Date, 101) AS Transaction_Date,
    TRY_CONVERT(INT, Branch_ID) AS Branch_ID,
    NULLIF(TRIM(Branch_Name), '') AS Branch_Name,
    NULLIF(TRIM(District), '') AS District,
    NULLIF(TRIM(Province), '') AS Province,
    NULLIF(TRIM(Payment_Method), '') AS Payment_Method,
    NULLIF(TRIM(Customer_Gender), '') AS Customer_Gender,
    TRY_CONVERT(INT, Customer_Age) AS Customer_Age,
    NULLIF(TRIM(Customer_City), '') AS Customer_City,
    TRY_CONVERT(INT, Medicine_ID) AS Medicine_ID,
    NULLIF(TRIM(Medicine_Name), '') AS Medicine_Name,
    NULLIF(TRIM(Generic_Name), '') AS Generic_Name,
    NULLIF(TRIM(Medicine_Category), '') AS Medicine_Category,
    NULLIF(TRIM(Dosage_Form), '') AS Dosage_Form,
    TRY_CONVERT(DECIMAL(18,2), NULLIF(TRIM(Strength_mg), '')) AS Strength_mg,
    NULLIF(TRIM(Pack_Size), '') AS Pack_Size,
    NULLIF(TRIM(Supplier_Name), '') AS Supplier_Name,
    NULLIF(TRIM(Prescription_Required), '') AS Prescription_Required,
    NULLIF(TRIM(Batch_No), '') AS Batch_No,
    TRY_CONVERT(DATE, Expiry_Date, 101) AS Expiry_Date,
    TRY_CONVERT(INT, Quantity) AS Quantity,
    TRY_CONVERT(DECIMAL(18,2), Unit_Price_LKR) AS Unit_Price_LKR,
    TRY_CONVERT(DECIMAL(9,4), Discount_Rate) AS Discount_Rate,
    TRY_CONVERT(DECIMAL(18,2), Line_Total_LKR) AS Line_Total_LKR,
    TRY_CONVERT(INT, Year) AS [Year],
    TRY_CONVERT(INT, Month) AS [Month]
FROM stg.pharmacy_raw;
GO




