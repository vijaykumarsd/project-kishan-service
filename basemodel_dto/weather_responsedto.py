from pydantic import BaseModel
from typing import List

class CurrentWeather(BaseModel):
    temperature: float
    condition: str
    wind_kph: float
    precip_mm: float
    pressure_mb: float

class ForecastDay(BaseModel):
    date: str
    avg_temp: float
    condition: str
    icon_code: str

class LocationInfo(BaseModel):
    country: str
    region: str
    lat: float
    lon: float
    localtime: str
    timezone: str

class AstroInfo(BaseModel):
    sunrise: str
    sunset: str

class WeatherResponse(BaseModel):
    current: CurrentWeather
    forecast: List[ForecastDay]
    location: LocationInfo
    astro: AstroInfo
