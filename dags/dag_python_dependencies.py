# check certain library exsistence

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import importlib

default_args = {
  'owner': 'gabe',
  'retry_delay': timedelta(minutes = 5) ,
  'retries': 0,
}

def _get_lib():
  import openmeteo_requests
  print(f"package with version {openmeteo_requests.__version__}")

def get_lib():
    try:
        openmeteo_requests = importlib.import_module('openmeteo_requests')
        print("Package is installed!")
    except ImportError:
        print("Package is not installed.")

with DAG(
  default_args = default_args,
  dag_id = 'dag_python_dependency_v01',
  start_date = datetime(2021, 10, 16),
  schedule_interval = '@daily',
  catchup=False,
) as dag:
  
  get_lib = PythonOperator(
    task_id = 'get_lib',
    python_callable = get_lib
  )

  get_lib