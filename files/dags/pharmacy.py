import csv
import logging
import os
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from pendulum import datetime

try:
    import pymssql
except ImportError:
    pymssql = None

try:
    import pyodbc
except ImportError:
    pyodbc = None


DEFAULT_CSV_PATH = (
    Path(__file__).resolve().parents[1] / "Pharmacy_OLTP_SLStyle_18Months.csv"
)
AIRFLOW_CSV_PATH = Path(
    "/usr/local/airflow/include/Pharmacy_OLTP_SLStyle_18Months.csv"
)
BATCH_SIZE = 1000


def _quote_identifier(identifier):
    return f"[{identifier.replace(']', ']]')}]"


def _odbc_value(value):
    return "{" + value.replace("}", "}}") + "}"


def _required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable {name} is not set.")
    return value


def _get_csv_path(use_windows_auth=False):
    default_csv_path = DEFAULT_CSV_PATH if use_windows_auth else AIRFLOW_CSV_PATH
    return Path(os.getenv("PHARMACY_CSV_PATH", str(default_csv_path)))


def _get_connection_config(use_windows_auth=False):
    if use_windows_auth:
        if pyodbc is None:
            raise ImportError("pyodbc is required for Windows Authentication.")
        server = os.getenv("PHARMACY_SQL_SERVER", "lpc:localhost").strip()
        database = os.getenv(
            "PHARMACY_SQL_DATABASE",
            "PharmacyAnalyticsDB",
        ).strip()
        schema = os.getenv("PHARMACY_SQL_SCHEMA", "stg").strip()
        table = os.getenv(
            "PHARMACY_SQL_TABLE",
            "pharmacy_raw_staging",
        ).strip()
        driver = os.getenv(
            "PHARMACY_ODBC_DRIVER",
            "ODBC Driver 18 for SQL Server",
        ).strip()
        if not all((server, database, schema, table, driver)):
            raise ValueError(
                "PHARMACY_SQL_SERVER, PHARMACY_SQL_DATABASE, "
                "PHARMACY_SQL_SCHEMA, PHARMACY_SQL_TABLE, and "
                "PHARMACY_ODBC_DRIVER must not be empty."
            )

        connection_string = (
            f"DRIVER={_odbc_value(driver)};"
            f"SERVER={_odbc_value(server)};"
            f"DATABASE={_odbc_value(database)};"
            "Trusted_Connection=yes;"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )

        def connect():
            return pyodbc.connect(connection_string, timeout=30)

        parameter_marker = "?"
    else:
        if pymssql is None:
            raise ImportError("pymssql is required for SQL Server Authentication.")
        server = _required_env("MSSQL_HOST")
        database = _required_env("MSSQL_DATABASE")
        username = _required_env("MSSQL_USERNAME")
        password = _required_env("MSSQL_PASSWORD")
        schema = os.getenv("MSSQL_SCHEMA", "stg").strip()
        table = os.getenv(
            "MSSQL_TABLE",
            "pharmacy_raw_staging",
        ).strip()
        if not schema or not table:
            raise ValueError("MSSQL_SCHEMA and MSSQL_TABLE must not be empty.")

        try:
            port = int(os.getenv("MSSQL_PORT", "1433"))
        except ValueError as error:
            raise ValueError("MSSQL_PORT must be an integer.") from error
        if not 1 <= port <= 65535:
            raise ValueError("MSSQL_PORT must be between 1 and 65535.")

        def connect():
            return pymssql.connect(
                server=server,
                port=port,
                user=username,
                password=password,
                database=database,
                login_timeout=30,
                timeout=600,
                charset="UTF-8",
            )

        parameter_marker = "%s"

    return connect, schema, table, parameter_marker


def extract_csv(use_windows_auth=False):
    csv_path = _get_csv_path(use_windows_auth)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        try:
            headers = next(reader)
        except StopIteration as error:
            raise ValueError(f"CSV file is empty: {csv_path}") from error

        if not headers or any(not header.strip() for header in headers):
            raise ValueError("CSV headers must not be empty.")
        if len({header.casefold() for header in headers}) != len(headers):
            raise ValueError("CSV headers must be unique, ignoring letter case.")

        row_count = 0
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(headers):
                raise ValueError(
                    f"CSV row {line_number} has {len(row)} fields; "
                    f"expected {len(headers)}."
                )
            row_count += 1

    logging.info(
        "Extracted and validated %d rows and %d columns from %s.",
        row_count,
        len(headers),
        csv_path,
    )
    return {
        "csv_path": str(csv_path),
        "headers": headers,
        "row_count": row_count,
    }


def connect_and_prepare_sql(use_windows_auth=False, **context):
    ti = context.get("ti")
    if ti:
        extract_info = ti.xcom_pull(task_ids="extract_csv")
        headers = extract_info["headers"]
    else:
        extract_info = extract_csv(use_windows_auth=use_windows_auth)
        headers = extract_info["headers"]

    connect, schema, table, parameter_marker = _get_connection_config(
        use_windows_auth
    )

    quoted_schema = _quote_identifier(schema)
    quoted_table = _quote_identifier(table)
    full_table = f"{quoted_schema}.{quoted_table}"
    column_definitions = ", ".join(
        f"{_quote_identifier(header)} NVARCHAR(MAX) NULL" for header in headers
    )

    create_schema_sql = (
        f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = {parameter_marker}) "
        f"EXEC('CREATE SCHEMA {quoted_schema}')"
    )

    create_or_truncate_table_sql = (
        "IF OBJECT_ID(QUOTENAME("
        f"{parameter_marker}) + N'.' + "
        f"QUOTENAME({parameter_marker}), N'U') IS NULL "
        f"CREATE TABLE {full_table} ({column_definitions}) "
        "ELSE "
        f"TRUNCATE TABLE {full_table}"
    )

    connection = connect()
    try:
        cursor = connection.cursor()
        try:
            if use_windows_auth:
                cursor.execute(create_schema_sql, schema)
                cursor.execute(create_or_truncate_table_sql, schema, table)
            else:
                cursor.execute(create_schema_sql, (schema,))
                cursor.execute(create_or_truncate_table_sql, (schema, table))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    finally:
        connection.close()

    logging.info(
        "Successfully connected to SQL Server and prepared table %s.%s.",
        schema,
        table,
    )
    return {"schema": schema, "table": table}


def load_data_to_sql(use_windows_auth=False, **context):
    ti = context.get("ti")
    if ti:
        extract_info = ti.xcom_pull(task_ids="extract_csv")
        csv_path = Path(extract_info["csv_path"])
        headers = extract_info["headers"]
    else:
        csv_path = _get_csv_path(use_windows_auth)
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            headers = next(csv.reader(f))

    connect, schema, table, parameter_marker = _get_connection_config(
        use_windows_auth
    )

    quoted_schema = _quote_identifier(schema)
    quoted_table = _quote_identifier(table)
    full_table = f"{quoted_schema}.{quoted_table}"

    insert_sql = (
        f"INSERT INTO {full_table} "
        f"({', '.join(_quote_identifier(header) for header in headers)}) "
        f"VALUES ({', '.join(parameter_marker for _ in headers)})"
    )

    inserted_rows = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        next(reader)

        connection = connect()
        try:
            cursor = connection.cursor()
            try:
                batch = []
                for row in reader:
                    batch.append(row)
                    if len(batch) >= BATCH_SIZE:
                        cursor.executemany(insert_sql, batch)
                        inserted_rows += len(batch)
                        batch.clear()

                if batch:
                    cursor.executemany(insert_sql, batch)
                    inserted_rows += len(batch)

                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
        finally:
            connection.close()

    logging.info(
        "Inserted %d rows from %s into %s.%s.",
        inserted_rows,
        csv_path,
        schema,
        table,
    )
    return inserted_rows


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    extract_csv(use_windows_auth=True)
    connect_and_prepare_sql(use_windows_auth=True)
    total = load_data_to_sql(use_windows_auth=True)
    print(f"Inserted {total} rows.")
else:
    with DAG(
        dag_id="pharmacy_csv_to_sql_server",
        description="Extract pharmacy CSV, connect/prepare SQL Server, and load data.",
        start_date=datetime(2024, 1, 1),
        schedule=None,
        catchup=False,
        default_args={"retries": 2},
        tags=["pharmacy", "sql-server", "etl"],
    ) as dag:

        extract_task = PythonOperator(
            task_id="extract_csv",
            python_callable=extract_csv,
        )

        connect_sql_task = PythonOperator(
            task_id="connect_to_sql_server",
            python_callable=connect_and_prepare_sql,
        )

        load_data_task = PythonOperator(
            task_id="load_data_to_sql_server",
            python_callable=load_data_to_sql,
        )

        extract_task >> connect_sql_task >> load_data_task
