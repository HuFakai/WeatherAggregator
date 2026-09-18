import requests
import time
from typing import List, Dict
from app.worker.fetchers.base import BaseFetcher
from app.worker.fetchers.registry import FetcherRegistry
from app.models.weather import StandardDailyWeather, LifestyleIndex
from app.core.logger import logger

@FetcherRegistry.register("yiketianqi")
class YiKeFetcher(BaseFetcher):
    """
    一客天气 (Yiketianqi) 抓取器实现
    负责调用一客天气 API 获取天气数据并进行标准化
    """
    CHANNEL_NAME = "yiketianqi"
    BASE_URL = "http://v1.yiketianqi.com/api"

    def fetch(self, city_code: str) -> Dict:
        """
        抓取易客天气数据
        """
        # 1. 查询城市名称
        city_doc = self.key_manager.db.cities.find_one({"_id": city_code})
        if not city_doc:
            raise Exception(f"City not found for adcode: {city_code}")
        
        city_name = city_doc.get("name")
        search_city_name = city_name
        if len(city_name) >= 3:
            if search_city_name.endswith("市") or search_city_name.endswith("区") or search_city_name.endswith("县"):
                 search_city_name = search_city_name[:-1]

        while True:
            # 2. 获取 Key
            key_str = self.key_manager.get_key(self.CHANNEL_NAME)
            if not key_str:
                # 如果没有可用 Key，尝试使用默认测试 Key
                key_str = "62179544|xP54U2zh" 

            try:
                if "|" in key_str:
                    appid, appsecret = key_str.split("|")
                else:
                    logger.error(f"[{self.CHANNEL_NAME}] Key 格式无效: {key_str}")
                    self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str)
                    continue

                # 定义请求函数
                def do_request(params_dict):
                    base_params = {
                        "unescape": 1,
                        "version": "v9",
                        "appid": appid,
                        "appsecret": appsecret,
                    }
                    base_params.update(params_dict)
                    resp = requests.get(self.BASE_URL, params=base_params, timeout=5)
                    return resp.json()

                # 3. 尝试策略
                data = {}
                
                # 策略 0: 优先使用 Adcode (city_code)
                # 注意: 易客天气 API 参数为 adcode
                adcode = city_doc.get("adcode")
                logger.info(f"[{self.CHANNEL_NAME}] 正在使用 Adcode {adcode} 抓取 {city_name} (Key: {key_str})...")
                data = do_request({"adcode": adcode})
                if "data" not in data:
                    errmsg = data.get("errmsg", "")
                    logger.info(f"[{self.CHANNEL_NAME}] Adcode {adcode} 抓取 {city_name} 失败: {errmsg}。尝试回退到 City ID 策略...")
                    
                    # 策略 1: 使用 City ID
                    yike_id = city_doc.get("mappings", {}).get("yike", {}).get("id")
                    if yike_id:
                        data = do_request({"cityid": yike_id})
                    else:
                        logger.info(f"[{self.CHANNEL_NAME}] {city_name} 无 City ID，跳过策略 1。")
                        
                    if "data" not in data:
                        if yike_id:
                            errmsg = data.get("errmsg", "")
                            logger.info(f"[{self.CHANNEL_NAME}] City ID {yike_id} 失败: {errmsg}。尝试回退到名称策略...")
                        
                        # 策略 2: 使用城市名称
                        data = do_request({"city": search_city_name})
                        
                        if "data" not in data:
                            errmsg = data.get("errmsg", "")
                            
                            # 检查是否为频率限制或 Key 无效
                            # 常见错误: "101010100: frequency limit", "ip limit", "key expire", "appid error"
                            lower_msg = errmsg.lower()
                            if any(k in lower_msg for k in ["frequency", "limit", "expire", "appid", "secret", "auth", "过期", "无效"]):
                                logger.error(f"[{self.CHANNEL_NAME}] Key {key_str} 失效/限流: {errmsg}")
                                # 检查是否需要标记 Key 失效
                                if "frequency" in errmsg or "limit" in errmsg or "expire" in errmsg:
                                    # 限额类错误，标记失效直到午夜
                                    self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, until_midnight=True)
                                elif "appid" in errmsg or "secret" in errmsg or "auth" in errmsg:
                                    # 权限类错误，标记失效 24 小时 (或更久)
                                    self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, duration=86400)
                                continue # 换 Key 重试
                            
                            # 检查是否为城市不存在
                            if "city" in lower_msg and "exist" in lower_msg or "adcode" in lower_msg:
                                # 视为致命错误，不换 Key
                                raise Exception(f"[{self.CHANNEL_NAME}] 城市未找到 (Adcode, ID & 名称均失败): {city_name}/{city_code}, Err: {errmsg}")
                                
                            # 其他未知错误，记录详细日志但不轻易废弃 Key (可能是临时服务波动)
                            logger.error(f"[{self.CHANNEL_NAME}] API 未知错误 (Key: {key_str}): {data}")
                            # 只有明确是 Key 问题才 mark_invalid，否则可能是参数问题或服务端问题
                            # self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str) 
                            # 暂时抛出异常结束当前城市抓取，避免死循环
                            raise Exception(f"[{self.CHANNEL_NAME}] API 请求失败: {errmsg}")

                return data

            except requests.RequestException as e:
                logger.error(f"[{self.CHANNEL_NAME}] 网络错误 (Key: {key_str}): {e}")
                # 网络错误不应废弃 Key，除非是 401/403 (但在 requests 异常中通常是连接问题)
                # 如果是 HTTPError 可以检查 status_code
                # 这里选择不废弃 Key，直接抛出异常让上层重试或跳过
                raise e

    def normalize(self, raw_data: Dict) -> List[StandardDailyWeather]:
        """
        数据清洗与标准化
        """
        results = []
        forecasts = raw_data.get("data", [])
        
        for item in forecasts:
            # 提取生活指数
            lifestyle_raw = item.get("index", [])
            lifestyle_list = []
            for life_item in lifestyle_raw:
                lifestyle_list.append(LifestyleIndex(
                    title=life_item.get("title", ""),
                    level=life_item.get("level", ""),
                    desc=life_item.get("desc", "")
                ))

            # 提取字段
            date = item.get("date")
            
            # 温度处理
            def parse_temp(t_str):
                if not t_str: return 0
                return int(str(t_str).replace("℃", ""))

            temp_high = parse_temp(item.get("tem1"))
            temp_low = parse_temp(item.get("tem2"))
            
            weather_day = item.get("wea_day")
            weather_night = item.get("wea_night")
            
            # 湿度处理
            humidity_str = str(item.get("humidity", "0")).replace("%", "")
            try:
                humidity = int(humidity_str)
            except ValueError:
                humidity = 0

            # 风向风力
            win_list = item.get("win", [])
            wind_direction = win_list[0] if win_list else "无持续风向"
            wind_scale = item.get("win_speed", "")

            # AQI 处理 (修复空字符串导致验证失败的问题)
            aqi_val = item.get("air", 0)
            if aqi_val == "":
                aqi_val = 0
            try:
                aqi = int(aqi_val)
            except (ValueError, TypeError):
                aqi = 0

            weather = StandardDailyWeather(
                date=date,
                temp_high=temp_high,
                temp_low=temp_low,
                weather_day=weather_day,
                weather_night=weather_night,
                humidity=humidity,
                wind_direction=wind_direction,
                wind_scale=wind_scale,
                aqi=aqi,
                aqi_level=item.get("air_level", ""),
                lifestyle=lifestyle_list
            )
            results.append(weather)
            
        return results
