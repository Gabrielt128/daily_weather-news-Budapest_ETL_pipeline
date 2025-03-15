from datetime import datetime, timedelta, timezone
# import openmeteo_requests
# import pandas as pd
import json
import urllib.request
import os

from airflow.models import Variable
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
  schedule_interval='0 7 * * *',
  catchup=True,
)
def weather_etl():
  @task
  def weather_extract():
    # according to the best practice in airflow, we should avoid import
    # expensive package like pandas in the top level code
    import pandas as pd
    import openmeteo_requests
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
    hourly_json = hourly_df.to_dict('records')
    return hourly_json
  
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

      CREATE TABLE IF NOT EXISTS budapest_news(
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        time TEXT NOT NULL
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
    return "Both table created"
  
  @task
  def news_extract():
    # the api key is set as the environment in .env
    apikey = Variable.get("api_key")
    now_utc = datetime.now(timezone.utc)
    iso_format = now_utc.isoformat(timespec='seconds').replace("+00:00", "Z")
    keyword = "Hungary"
    url = (f"https://gnews.io/api/v4/search?q={keyword}&lang=en&country=uk&max=100&apikey={apikey}"
    f"&in=description&in=title&from={iso_format}")
    with urllib.request.urlopen(url) as response:
      data = json.loads(response.read().decode("utf-8"))
      articles = data["articles"]
      titles = [article['title'] for article in articles]
      descriptions = [article['description'] for article in articles]
      times = [article['publishedAt'] for article in articles]
    return {"titles": titles, "descriptions": descriptions, "times":times}


  @task
  def data_load(weather_data, news_data):
    if not weather_data:
      raise ValueError("No book data found")
    hook = PostgresHook(postgres_conn_id="weather_connect")
    insert_query = """
    INSERT INTO budapest_weather (date, apparent_temperature)
    VALUES (%s, %s);
    """
    for data in weather_data:
      hook.run(insert_query, parameters=(data['date'], data['apparent_temperature']))

    insert_query2 = """
    INSERT INTO budapest_news (title, description, time)
    VALUES (%s, %s, %s);
    """
    for title, description, time in zip(news_data["titles"], news_data["descriptions"], news_data["times"]):
      hook.run(insert_query2, parameters=(title, description, time))

  @task
  def email(weathers, news):
    """
    We use the gmail/hotmail as host, but these
    services upgrade security rules of third party login.
    Google banned less secure log in, makes smtp connnection here fail

    Sendgrid:
    This part need api key from sendgrid,
    general users can't get the access.
    """
    pass

  weathers = weather_extract()
  news = news_extract()
  table_created = create_table()

  table_created >> data_load(weathers, news)
  email(
    weathers=weathers,
    news=news
  )

etl_object = weather_etl()