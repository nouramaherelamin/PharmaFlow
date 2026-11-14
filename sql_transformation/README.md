# PharmaFlow — SQL Transformation

## Purpose
This folder contains the SQL Server transformation layer for the PharmaFlow pharmacy sales ELT project. The source is loaded into staging, cleaned through SQL views, and validated before downstream Data Warehouse loading.

## Database objects
- Database: `PharmacyDB` (adjust the database name for the target environment).
- Expected source table: `stg.pharmacy_raw`.
- Cleaning view: `clean.vw_pharmacy_sales`.
- Business view: `clean.vw_pharmacy_sales_enriched`.
- Validation procedures:
  - `clean.usp_validate_technical`
  - `clean.usp_validate_business_rules`
  - `clean.usp_validate_final`

## Deployment order (one-time, and whenever definitions change)
1. Create the `clean` schema.
2. Create the cleaning view.
3. Create the business transformation view.
4. Create/update the three validation stored procedures.

Run `CREATE OR ALTER VIEW` / `CREATE OR ALTER PROCEDURE` statements in separate SQL Server batches. `GO` is a client-side batch separator (SSMS/sqlcmd), not a T-SQL command; an Airflow database hook must not send it unchanged to SQL Server.

## Per-run pipeline order
1. Load the CSV into `stg.pharmacy_raw`.
2. `EXEC clean.usp_validate_technical;`
3. `EXEC clean.usp_validate_business_rules;`
4. `EXEC clean.usp_validate_final;`
5. If all checks succeed, hand off `clean.vw_pharmacy_sales_enriched` to the Data Warehouse load.

The views are virtual and query current staging data; they do not need a refresh task after every load.

## Known integration checks
- The original loader's default staging table name was `stg.pharmacy_raw_staging`, while these views expect `stg.pharmacy_raw`. Align the actual Airflow configuration **before** running the DAG.
- The original loader truncates and reloads its target staging table. Confirm backup, permissions, and reload strategy before execution.
- SQL errors raised using `THROW` must propagate to Airflow so failed validations block downstream tasks.
- Test the full DAG separately; successful manual SSMS tests do not prove end-to-end Airflow execution.

## Dataset validation snapshot
Manual testing on the current restored dataset showed 50,000 source and transformed rows and 50,000 distinct transaction IDs. 31,236 `Strength_mg` values were missing and retained as NULL. Reconciliation allowed up to 0.01 LKR difference per transaction. Re-run checks for new data.

## Scope
This folder provides transformation and validation logic. The Star Schema, fact/dimension table creation, loading, and warehouse reconciliation are separate deliverables.

## Git workflow
Commit these SQL source files and this README to your feature branch, then open a pull request to `main`. Do not commit local database backups, credentials, or raw datasets unless the team has explicitly approved publishing them.
