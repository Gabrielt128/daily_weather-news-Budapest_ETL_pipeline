from datetime import datetime, timedelta
import openmeteo_requests
import pandas as pd

from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook


default_args = {
  'owner': 'airflow',
  'depends_on_past': False,
  'start_date': datetime(2024, 6, 20),
  'retries': 0,
  'retry_delay': timedelta(minutes=1),
}

@dag(
  dag_id = 'budapest_weather_email',
  default_args = default_args,
  catchup=False,
  schedule_interval=None,
)
def weather_etl():
  @task
  def weather_extract():
    om = openmeteo_requests.Client()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
      "latitude": [47.4984],
      "longitude": [19.0404],
      "hourly": "apparent_temperature",
      "forecast_days": 1
    }
    responses = om.weather_api(url, params=params)
    hourly = responses[0].Hourly()
    hourly_apparent_temperature = hourly.Variables(0).ValuesAsNumpy()
    hourly_df = pd.date_range(
      start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
      end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
      freq = pd.Timedelta(seconds = hourly.Interval()),
      inclusive = "left"
    ).strftime("%m/%d/%Y_%H").to_frame(index = False, name = 'date')
    
    hourly_df['apparent_temperature'] = hourly_apparent_temperature
    # hourly_json = hourly_df.to_json(orient = 'columns')
    hourly_json = hourly_df.to_dict('records')
    return hourly_json

  @task
  def transform(weather, new):
    """
    Transform weather and news prepare for the email
    """
    pass
  
  @task
  def create_table():
    hook = PostgresHook(postgres_conn_id="weather_connect")

    create_sql = """
    DO $$
    DECLARE 
      record_count INT;
    BEGIN 
      CREATE TABLE IF NOT EXISTS budapest_weather (
        id SERIAL PRIMARY KEY,
        date TEXT NOT NULL,
        apparent_temperature FLOAT
      );

      record_count = (SELECT COUNT(*) FROM budapest_weather);
      IF record_count >= 168 THEN
        DROP TABLE budapest_weather;
        RAISE NOTICE 'we just cleard the past 7 days';

        CREATE TABLE budapest_weather (
          id SERIAL PRIMARY KEY,
          date TEXT NOT NULL,
          apparent_temperature FLOAT
        );
      END IF;

    END $$;
    """
    hook.run(create_sql)
    return "Table created"


  @task
  def weather_load(weather_data):
    print(type(weather_data))
    if not weather_data:
      raise ValueError("No book data found")
    hook = PostgresHook(postgres_conn_id="weather_connect")
    insert_query = """
    INSERT INTO budapest_weather (date, apparent_temperature)
    VALUES (%s, %s)
    """
    for data in weather_data:
      hook.run(insert_query, parameters=(data['date'], data['apparent_temperature']))

  responses = weather_extract()
  # weather_data = weather_transform(responses)
  table_created = create_table()
  table_created >> weather_load(responses)
  

etl_object = weather_etl()