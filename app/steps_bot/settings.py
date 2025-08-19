from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    BOT_TOKEN: str
    WEBHOOK_URL: str
    
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[int] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    
    CDEK_ACCOUNT: Optional[str] = None
    CDEK_SECURE: Optional[str] = None
    CDEK_TEST_MODE: bool = False
    CDEK_API_URL: str = "https://api.cdek.ru/v2"
    CDEK_TEST_API_URL: str = "https://api.edu.cdek.ru/v2"

    CDEK_FROM_CITY_CODE: Optional[int] = None
    CDEK_TARIFF_PVZ: int = 136
    CDEK_TARIFF_COURIER: int = 137

    DEFAULT_PACKAGE_WEIGHT_G: int = 500
    DEFAULT_PACKAGE_L: int = 20
    DEFAULT_PACKAGE_W: int = 15
    DEFAULT_PACKAGE_H: int = 10
    
    model_config = SettingsConfigDict(env_file='.env')
    

config = Settings()