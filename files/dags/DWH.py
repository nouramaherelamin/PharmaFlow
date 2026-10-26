import os
import re
from pathlib import Path
from datetime import datetime
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

try:
    import pymssql
except ImportError:
    pymssql = None

try:
    import pyodbc
except ImportError:
    pyodbc = None

dwh_schema = os.getenv("MSSQL_DWH_SCHEMA", "dw")
INCLUDE_DIR = Path("/usr/local/airflow/include")

def get_db_connection():
    server = os.getenv("MSSQL_SERVER", "host.docker.internal")
    database = os.getenv("MSSQL_DATABASE", "PharmacyDB")
    user = os.getenv("MSSQL_USER", "sa")
    password = os.getenv("MSSQL_PASSWORD", "Ahmed#2007")
    port = os.getenv("MSSQL_PORT", "1433")

    if pymssql:
        return pymssql.connect(server=server, user=user, password=password, database=database, port=port, autocommit=True)
    elif pyodbc:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server},{port};DATABASE={database};UID={user};PWD={password}"
        return pyodbc.connect(conn_str, autocommit=True)
    else:
        raise RuntimeError("No SQL Server driver (pymssql or pyodbc) found!")

def execute_sql(sql_input):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    queries = sql_input if isinstance(sql_input, list) else [sql_input]
    
    for item in queries:
        file_path = INCLUDE_DIR / item
        if file_path.exists() and file_path.is_file():
            sql_text = file_path.read_text(encoding="utf-8")
        else:
            sql_text = item
            
        batches = re.split(r'^\s*GO\s*$', sql_text, flags=re.MULTILINE | re.IGNORECASE)
        for batch in batches:
            if batch.strip():
                cursor.execute(batch)
                
    cursor.close()
    conn.close()

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 0
}

with DAG(
    'pharmacy_dwh_pipeline', 
    default_args=default_args, 
    schedule=None, 
    catchup=False
) as dag:

    deploy_clean_objects = PythonOperator(
        task_id='deploy_clean_objects',
        python_callable=execute_sql,
        op_kwargs={'sql_input': [
            '01_create_clean_schema.sql',
            '02_create_clean_view.sql',
            '03_create_business_view.sql',
            '04_create_technical_validation_procedure.sql',
            '05_create_business_rules_procedure.sql',
            '06_create_final_validation_procedure.sql'
        ]}
    )

    run_technical_validation = PythonOperator(
        task_id='run_technical_validation',
        python_callable=execute_sql,
        op_kwargs={'sql_input': "EXEC clean.usp_validate_technical;"}
    )

    run_business_validation = PythonOperator(
        task_id='run_business_validation',
        python_callable=execute_sql,
        op_kwargs={'sql_input': "EXEC clean.usp_validate_business_rules;"}
    )

    run_final_validation = PythonOperator(
        task_id='run_final_validation',
        python_callable=execute_sql,
        op_kwargs={'sql_input': "EXEC clean.usp_validate_final;"}
    )

    load_dim_medicine = PythonOperator(
        task_id='load_dim_medicine',
        python_callable=execute_sql,
        op_kwargs={'sql_input': f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Dim_Medicine' AND schema_id = SCHEMA_ID('{dwh_schema}'))
            BEGIN
                CREATE TABLE {dwh_schema}.Dim_Medicine (
                    Medicine_ID INT PRIMARY KEY, 
                    Medicine_Name NVARCHAR(MAX), 
                    Generic_Name NVARCHAR(MAX), 
                    Medicine_Category NVARCHAR(MAX), 
                    Dosage_Form NVARCHAR(MAX), 
                    Strength_mg DECIMAL(18,2), 
                    Prescription_Required NVARCHAR(50)
                );
            END;
            
            INSERT INTO {dwh_schema}.Dim_Medicine 
            SELECT DISTINCT Medicine_ID, Medicine_Name, Generic_Name, Medicine_Category, Dosage_Form, Strength_mg, Prescription_Required 
            FROM clean.vw_pharmacy_sales_enriched 
            WHERE Medicine_ID IS NOT NULL 
            AND Medicine_ID NOT IN (SELECT Medicine_ID FROM {dwh_schema}.Dim_Medicine);
        """}
    )

    load_dim_branch = PythonOperator(
        task_id='load_dim_branch',
        python_callable=execute_sql,
        op_kwargs={'sql_input': f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Dim_Branch' AND schema_id = SCHEMA_ID('{dwh_schema}'))
            BEGIN
                CREATE TABLE {dwh_schema}.Dim_Branch (
                    Branch_ID INT PRIMARY KEY, 
                    Branch_Name NVARCHAR(MAX), 
                    District NVARCHAR(MAX), 
                    Province NVARCHAR(MAX)
                );
            END;
            
            INSERT INTO {dwh_schema}.Dim_Branch 
            SELECT DISTINCT Branch_ID, Branch_Name, District, Province 
            FROM clean.vw_pharmacy_sales_enriched 
            WHERE Branch_ID IS NOT NULL 
            AND Branch_ID NOT IN (SELECT Branch_ID FROM {dwh_schema}.Dim_Branch);
        """}
    )

    load_dim_date = PythonOperator(
        task_id='load_dim_date',
        python_callable=execute_sql,
        op_kwargs={'sql_input': f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Dim_Date' AND schema_id = SCHEMA_ID('{dwh_schema}'))
            BEGIN
                CREATE TABLE {dwh_schema}.Dim_Date (
                    Transaction_Date DATE PRIMARY KEY, 
                    Year INT, 
                    Month INT
                );
            END;
            
            INSERT INTO {dwh_schema}.Dim_Date 
            SELECT DISTINCT Transaction_Date, Year, Month 
            FROM clean.vw_pharmacy_sales_enriched 
            WHERE Transaction_Date IS NOT NULL 
            AND Transaction_Date NOT IN (SELECT Transaction_Date FROM {dwh_schema}.Dim_Date);
        """}
    )

    load_dim_customer = PythonOperator(
        task_id='load_dim_customer',
        python_callable=execute_sql,
        op_kwargs={'sql_input': f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Dim_Customer' AND schema_id = SCHEMA_ID('{dwh_schema}'))
            BEGIN
                CREATE TABLE {dwh_schema}.Dim_Customer (
                    Customer_ID INT IDENTITY(1,1) PRIMARY KEY, 
                    Customer_Gender NVARCHAR(50), 
                    Customer_Age INT, 
                    Customer_City NVARCHAR(MAX)
                );
            END;
            
            INSERT INTO {dwh_schema}.Dim_Customer (Customer_Gender, Customer_Age, Customer_City)
            SELECT DISTINCT Customer_Gender, Customer_Age, Customer_City 
            FROM clean.vw_pharmacy_sales_enriched 
            WHERE (Customer_Gender IS NOT NULL OR Customer_Age IS NOT NULL OR Customer_City IS NOT NULL)
            AND NOT EXISTS (
                SELECT 1 FROM {dwh_schema}.Dim_Customer dc 
                WHERE ISNULL(dc.Customer_Gender, '') = ISNULL(clean.vw_pharmacy_sales_enriched.Customer_Gender, '')
                AND ISNULL(dc.Customer_Age, 0) = ISNULL(clean.vw_pharmacy_sales_enriched.Customer_Age, 0)
                AND ISNULL(dc.Customer_City, '') = ISNULL(clean.vw_pharmacy_sales_enriched.Customer_City, '')
            );
        """}
    )

    load_fact_sales = PythonOperator(
        task_id='load_fact_sales',
        python_callable=execute_sql,
        op_kwargs={'sql_input': f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Fact_Sales' AND schema_id = SCHEMA_ID('{dwh_schema}'))
            BEGIN
                CREATE TABLE {dwh_schema}.Fact_Sales (
                    Transaction_ID INT PRIMARY KEY, 
                    Transaction_Date DATE, 
                    Branch_ID INT, 
                    Medicine_ID INT, 
                    Quantity INT, 
                    Unit_Price_LKR DECIMAL(18,2), 
                    Discount_Rate DECIMAL(9,4), 
                    Line_Total_LKR DECIMAL(18,2), 
                    Gross_Sales_LKR DECIMAL(18,2), 
                    Discount_Amount_LKR DECIMAL(18,2), 
                    Calculated_Net_Sales_LKR DECIMAL(18,2), 
                    Days_To_Expiry INT
                );
            END;
            
            INSERT INTO {dwh_schema}.Fact_Sales 
            SELECT Transaction_ID, Transaction_Date, Branch_ID, Medicine_ID, Quantity, Unit_Price_LKR, Discount_Rate, Line_Total_LKR, Gross_Sales_LKR, Discount_Amount_LKR, Calculated_Net_Sales_LKR, Days_To_Expiry 
            FROM clean.vw_pharmacy_sales_enriched 
            WHERE Transaction_ID NOT IN (SELECT Transaction_ID FROM {dwh_schema}.Fact_Sales);
        """}
    )

    deploy_clean_objects >> run_technical_validation >> run_business_validation >> run_final_validation
    
    run_final_validation >> [load_dim_medicine, load_dim_branch, load_dim_date, load_dim_customer] >> load_fact_sales