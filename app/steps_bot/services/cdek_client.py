import time
from typing import Any, Dict, List, Optional

import aiohttp

from app.steps_bot.settings import config
from app.steps_bot.services.cdek_errors import CDEKAuthError, CDEKApiError


class CDEKClient:
    """Клиент для работы с API СДЭК: токен, справочники, создание заказа."""

    def __init__(self) -> None:
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    @property
    def base_url(self) -> str:
        """Возвращает базовый URL API в зависимости от режима."""
        return (config.CDEK_TEST_API_URL if config.CDEK_TEST_MODE else config.CDEK_API_URL).rstrip("/")

    async def _ensure_token(self, session: aiohttp.ClientSession) -> str:
        """Обеспечивает валидный access_token, обновляет при необходимости."""
        if self._access_token and time.time() < self._expires_at - 30:
            return self._access_token

        url = f"{self.base_url}/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": config.CDEK_ACCOUNT or "",
            "client_secret": config.CDEK_SECURE or "",
        }
        async with session.post(url, headers=headers, data=data, timeout=20) as resp:
            text = await resp.text()
            if resp.status == 401:
                raise CDEKAuthError("Неверные учетные данные CDEK или среда API не совпадает.")
            if resp.status >= 500:
                raise CDEKApiError(f"Ошибка получения токена CDEK: {resp.status} {text}")
            payload: Dict[str, Any] = await resp.json()
            self._access_token = payload.get("access_token") or ""
            expires_in = int(payload.get("expires_in", 0))
            self._expires_at = time.time() + max(expires_in, 0)
            return self._access_token

    async def find_city_code(self, city: str) -> Optional[int]:
        """Возвращает код города по названию."""
        params = {"city": city}
        async with aiohttp.ClientSession() as session:
            token = await self._ensure_token(session)
            headers = {"Authorization": f"Bearer {token}"}
            url = f"{self.base_url}/location/cities"
            async with session.get(url, headers=headers, params=params, timeout=20) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise CDEKAuthError("Авторизация CDEK отклонена.")
                if resp.status >= 500:
                    raise CDEKApiError(f"Ошибка справочника городов: {resp.status} {text}")
                items: List[Dict[str, Any]] = await resp.json()
                for item in items:
                    if str(item.get("city", "")).lower() == city.strip().lower():
                        return item.get("code")
                return items[0]["code"] if items else None

    async def list_pvz(self, city_code: int, page: int = 0, size: int = 10) -> List[Dict[str, Any]]:
        """Возвращает список ПВЗ по коду города."""
        params = {"city_code": city_code, "type": "PVZ", "page": page, "size": size}
        async with aiohttp.ClientSession() as session:
            token = await self._ensure_token(session)
            headers = {"Authorization": f"Bearer {token}"}
            url = f"{self.base_url}/deliverypoints"
            async with session.get(url, headers=headers, params=params, timeout=20) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise CDEKAuthError("Авторизация CDEK отклонена.")
                if resp.status >= 500:
                    raise CDEKApiError(f"Ошибка списка ПВЗ: {resp.status} {text}")
                items: List[Dict[str, Any]] = await resp.json()
                return items

    async def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Создает заказ доставки и возвращает ответ API."""
        async with aiohttp.ClientSession() as session:
            token = await self._ensure_token(session)
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            url = f"{self.base_url}/orders"
            async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise CDEKAuthError("Авторизация CДЭК отклонена.")
                if resp.status >= 500:
                    raise CDEKApiError(f"Ошибка создания заказа: {resp.status} {text}")
                if resp.status >= 400:
                    return {"ok": False, "status": resp.status, "text": text}
                data = await resp.json()
                return {"ok": True, "data": data}


cdek_client = CDEKClient()