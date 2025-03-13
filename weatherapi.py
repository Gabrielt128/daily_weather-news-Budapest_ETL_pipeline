import openmeteo_requests
import pandas as pd

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
  return responses

def weather_transformer(response):
  hourly = response.Hourly()
  hourly_apparent_temperature = hourly.Variables(0).ValuesAsNumpy()
  hourly_data = {"date": pd.date_range(
    start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
    end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
    freq = pd.Timedelta(seconds = hourly.Interval()),
    inclusive = "left"
  ).strftime("%m/%d/%Y_%H")}
  hourly_data["apparent_temperature"] = hourly_apparent_temperature
  hourly_dataframe = pd.DataFrame(data = hourly_data)
  return hourly_dataframe

if __name__ == "__main__":
  responses = weather_extract()
  df = weather_transformer(responses[0])
  print(df)

  for index, row in df.iterrows():
    print(row['apparent_temperature'])
  