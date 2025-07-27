# weather_tool.py
import os
import requests
from dotenv import load_dotenv
from basemodel_dto.weather_responsedto import WeatherResponse, CurrentWeather, ForecastDay, LocationInfo, AstroInfo

load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather_forecast(location: str) -> WeatherResponse:
    url = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": WEATHER_API_KEY,
        "q": location,
        "days": 5,
        "aqi": "yes",
        "alerts": "yes"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"{response.status_code} Error: {response.text}")

    data = response.json()

    return WeatherResponse(
        current=CurrentWeather(
            temperature=data["current"]["temp_c"],
            condition=data["current"]["condition"]["text"],
            wind_kph=data["current"]["wind_kph"],
            precip_mm=data["current"]["precip_mm"],
            pressure_mb=data["current"]["pressure_mb"]
        ),
        forecast=[
            ForecastDay(
                date=day["date"],
                avg_temp=day["day"]["avgtemp_c"],
                condition=day["day"]["condition"]["text"],
                icon_code=day["day"]["condition"]["icon"].split("/")[-1]
            )
            for day in data["forecast"]["forecastday"]
        ],
        location=LocationInfo(
            country=data["location"]["country"],
            region=data["location"]["region"],
            lat=data["location"]["lat"],
            lon=data["location"]["lon"],
            localtime=data["location"]["localtime"],
            timezone=data["location"]["tz_id"]
        ),
        astro=AstroInfo(
            sunrise=data["forecast"]["forecastday"][0]["astro"]["sunrise"],
            sunset=data["forecast"]["forecastday"][0]["astro"]["sunset"]
        )
    )
