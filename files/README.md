Overview
========

Welcome to Astronomer! This project was generated after you ran 'astro dev init' using the Astronomer CLI. This readme describes the contents of the project, as well as how to run Apache Airflow on your local machine.

Project Contents
================

Your Astro project contains the following files and folders:

- dags: This folder contains the Python files for your Airflow Dags. By default, this directory includes one example Dag:
    - `example_astronauts`: This Dag shows a simple ETL pipeline example that queries the list of astronauts currently in space from the Open Notify API and prints a statement for each astronaut. The Dag uses the TaskFlow API to define tasks in Python, and dynamic task mapping to dynamically print a statement for each astronaut. For more on how this Dag works, see our [Getting started tutorial](https://www.astronomer.io/docs/learn/get-started-with-airflow).
- Dockerfile: This file contains a versioned Astro Runtime Docker image that provides a differentiated Airflow experience. If you want to execute other commands or overrides at runtime, specify them here.
- include: This folder contains any additional files that you want to include as part of your project. It is empty by default.
- packages.txt: Install OS-level packages needed for your project by adding them to this file. It is empty by default.
- requirements.txt: Install Python packages needed for your project by adding them to this file. It is empty by default.
- plugins: Add custom or community plugins for your project to this file. It is empty by default.
- airflow_settings.yaml: Use this local-only file to specify Airflow Connections, Variables, and Pools instead of entering them in the Airflow UI as you develop Dags in this project.

Deploy Your Project Locally
===========================

Start Airflow on your local machine by running 'astro dev start'.

This command will spin up five Docker containers on your machine, each for a different Airflow component:

- Postgres: Airflow's Metadata Database
- Scheduler: The Airflow component responsible for monitoring and triggering tasks
- Dag Processor: The Airflow component responsible for parsing Dags
- API Server: The Airflow component responsible for serving the Airflow UI and API
- Triggerer: The Airflow component responsible for triggering deferred tasks

When all five containers are ready the command will open the browser to the Airflow UI at http://localhost:8080/. You should also be able to access your Postgres Database at 'localhost:5432/postgres' with username 'postgres' and password 'postgres'.

Note: If you already have either of the above ports allocated, you can either [stop your existing Docker containers or change the port](https://www.astronomer.io/docs/astro/cli/troubleshoot-locally#ports-are-not-available-for-my-local-airflow-webserver).

Deploy Your Project to Astronomer
=================================

If you have an Astronomer account, pushing code to a Deployment on Astronomer is simple. For deploying instructions, refer to Astronomer documentation: https://www.astronomer.io/docs/astro/deploy-code/

Contact
=======

The Astronomer CLI is maintained with love by the Astronomer team. To report a bug or suggest a change, reach out to our support.

Load the pharmacy CSV into SQL Server
=====================================

The `pharmacy_csv_to_sql_server` DAG reads the CSV in batches and appends its rows
to a SQL Server table. It creates the table if it does not exist, using the CSV
headers as column names and `NVARCHAR(MAX)` for each column. Each DAG run appends
rows; rerunning it will insert the data again.

Astro runs Airflow in Docker, so the Windows Downloads folder is not visible to
the DAG by default. From the project root, copy the CSV into the mounted `include`
folder:

```powershell
Copy-Item 'C:\Users\original\Downloads\Pharmacy_OLTP_SLStyle_18Months.csv' '.\include\Pharmacy_OLTP_SLStyle_18Months.csv'
```

The `pharmacy_csv_to_sql_server` DAG is defined in `dags/pharmacy.py`. It uses
`MSSQL_HOST`, `MSSQL_PORT`, `MSSQL_DATABASE`, `MSSQL_USERNAME`, and
`MSSQL_PASSWORD` from the Airflow environment. The CSV must be in the project's
`include` folder, which is mounted at `/usr/local/airflow/include` in Astro. Set
the SQL Server host to an address reachable from Docker (often
`host.docker.internal` for a local SQL Server), enable TCP/IP on SQL Server, and
use a SQL Server login; Windows Authentication from the host does not pass
through to the Astro container. Configure the variables in `.env` for local
development or in the Astro Deployment environment settings when deployed.
Trigger the DAG manually after the file and connection settings are in place.
Each run appends rows.

Windows authentication from the host
====================================

To load directly from Windows without a SQL password, run `dags/pharmacy.py`
from the project root. This uses the Windows user's integrated SQL Server
authentication to connect to the local default instance and defaults to
`PharmacyAnalyticsDB` and the CSV in the project root. This mode is independent
of Airflow; the DAG task uses SQL credentials as described above.

From the project root in PowerShell:

```powershell
python -m pip install -r .\scripts\requirements-windows.txt
python .\dags\pharmacy.py
```

The machine needs the Microsoft ODBC Driver 18 for SQL Server, and the Windows
account running the script needs permission to create and insert into the target
table. Optional `PHARMACY_CSV_PATH`, `PHARMACY_SQL_SERVER`,
`PHARMACY_SQL_DATABASE`, `PHARMACY_SQL_SCHEMA`, `PHARMACY_SQL_TABLE`, and
`PHARMACY_ODBC_DRIVER` environment variables can override the defaults. Do not
put a SQL password in this script; it uses Windows integrated authentication.
