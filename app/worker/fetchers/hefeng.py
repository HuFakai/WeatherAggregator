import requests
from typing import List, Dict
from app.worker.fetchers.base import BaseFetcher
from app.worker.fetchers.registry import FetcherRegistry
from app.models.weather import StandardDailyWeather
from app.core.logger import logger

@FetcherRegistry.register("hefeng")
class HeFengFetcher(BaseFetcher):
    """
    和风天气 (QWeather) 抓取器
    """
    CHANNEL_NAME = "hefeng"
  

    def fetch(self, city_id: str) -> Dict:
        """
        抓取和风天气数据
        """
        # 1. 获取和风 City ID
        city_doc = self.key_manager.db.cities.find_one({"_id": city_id})
        if not city_doc:
            raise Exception(f"City not found: {city_id}")
        
        # 2. 获取和风天气 location_id
        location_id = city_doc.get("mappings", {}).get("hefeng", {}).get("id")
        if not location_id:
            raise Exception(f"HeFeng ID not found for city: {city_doc.get('name')} ({city_id})")
        
        # 重试循环:当key失效时自动获取新key重试
        while True:
            # 3. 获取 Key
            key_str = self.key_manager.get_key(self.CHANNEL_NAME)

            if "|" in key_str:
                KEY_BASE_URL, key = key_str.split("|")
            else:
                logger.error(f"[{self.CHANNEL_NAME}] Key 格式无效: {key_str}")
                self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str)
                continue  # 获取下一个key重试
            
            # 确保BASE_URL包含协议
            if not KEY_BASE_URL.startswith("http://") and not KEY_BASE_URL.startswith("https://"):
                KEY_BASE_URL = "https://" + KEY_BASE_URL
                
            # 4. 调用 API
            BASE_URL = KEY_BASE_URL + "/v7/weather/7d"
            logger.info(f"[{self.CHANNEL_NAME}] 正在使用 location_id {location_id} 抓取 {city_doc.get('name')} (Key: {key_str})...")
            try:
                params = {
                    "location": location_id,
                    "key": key
                }
                response = requests.get(BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                code = data.get("code")
                if code != "200":
                    # 402: 超过日限额, 429: 超过QPM
                    if code in ["301", "302"]:
                        logger.warning(f"[{self.CHANNEL_NAME}] Key {key_str} 限额/频率超限 (Code: {code})")
                        self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, until_midnight=True)
                        continue  # 换key重试
                    elif code in ["401", "403"]:
                        logger.warning(f"[{self.CHANNEL_NAME}] Key {key_str} 认证失败 (Code: {code})")
                        self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, duration=86400)
                        continue  # 换key重试
                    else:
                        raise Exception(f"HeFeng API Error: {code}")
                    
                return data
            except requests.exceptions.RequestException as e:
                logger.error(f"[{self.CHANNEL_NAME}] Fetch failed for {location_id}: {e}")
                raise e

    def normalize(self, raw_data: Dict) -> List[StandardDailyWeather]:
        """
        标准化数据
        """
        results = []
        daily_list = raw_data.get("daily", [])
        
        for item in daily_list:
            # QWeather daily format:
            # fxDate, tempMax, tempMin, textDay, textNight, windDirDay, windScaleDay, humidity
            if item.get("windDirDay")==item.get("windDirNight"):
                wind_direction = item.get("windDirDay") # 假设字段: 白天风向
            else:
                wind_direction=item.get("windDirDay")+' 转 '+item.get("windDirNight")
            
            if item.get("windScaleDay")==item.get("windScaleNight"):
                    wind_scale = item.get("windScaleDay")+'级'    # 假设字段: 白天风力
            else:
                wind_scale=item.get("windScaleDay")+'级 转 '+item.get("windScaleNight")+'级'
                
            weather = StandardDailyWeather(
                date=item.get("fxDate"),
                temp_high=int(item.get("tempMax")),
                temp_low=int(item.get("tempMin")),
                weather_day=item.get("textDay"),
                weather_night=item.get("textNight"),
                humidity=int(item.get("humidity", 0)),
                wind_direction=wind_direction,
                wind_scale=wind_scale,
                lifestyle=[]
            )
            results.append(weather)
            
        return results
