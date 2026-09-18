import requests
import urllib.parse
import hashlib
from typing import List, Dict
from app.worker.fetchers.base import BaseFetcher
from app.worker.fetchers.registry import FetcherRegistry
from app.models.weather import StandardDailyWeather
from app.core.logger import logger

@FetcherRegistry.register("baidu")
class BaiduFetcher(BaseFetcher):
    """
    百度天气抓取器实现
    负责调用百度地图 API 获取天气数据并进行标准化
    """
    CHANNEL_NAME = "baidu"
    BASE_URL = "https://api.map.baidu.com/weather/v1/"

    def calculate_sn(self, params: Dict, sk: str) -> str:
        """
        计算百度 API SN 签名
        """
        # 1. 按照参数名排序并拼接字符串
        params_list = []
        for key in params:
            params_list.append(key + "=" + str(params[key]))
        
        # 注意: 百度示例代码中并没有显式排序，而是直接遍历 params
        # 但通常签名算法要求参数有序，或者 params 本身是有序字典
        # 百度示例: for key in params: paramsArr.append(key + "=" + params[key])
        # 这里我们保持原样，但为了稳健性，建议确保顺序一致性 (如果 API 对顺序敏感)
        # 实际上 requests.get 会自动 urlencode，但顺序可能不固定
        # 我们需要手动构建 query string 以确保计算 sn 的 string 和发送的一致
        
        # 修正: 我们需要构建一个 query string 用于计算 SN
        # 这里的 params 是字典
        
        # 重新参考示例:
        # paramsArr = []
        # for key in params: paramsArr.append(key + "=" + params[key])
        # queryStr = uri + "?" + "&".join(paramsArr)
        # encodedStr = urllib.request.quote(queryStr, safe="/:=&?#+!$,;'@()*[]")
        # rawStr = encodedStr + sk
        # sn = hashlib.md5(urllib.parse.quote_plus(rawStr).encode("utf8")).hexdigest()
        
        # 我们的 BASE_URL 是 https://api.map.baidu.com/weather/v1/
        # uri应该是 /weather/v1/
        uri = "/weather/v1/"
        
        # 构造 query string (未编码)
        # 必须保证顺序? 示例没提，但通常是需要的。
        # 这里我们直接用 urllib.parse.urlencode 来生成 query string，它默认不排序?
        # 示例是用 list append，说明顺序取决于 params 迭代顺序
        
        # 为了简单且正确，我们完全复刻示例逻辑
        params_arr = []
        for key in params:
            params_arr.append(f"{key}={params[key]}")
            
        query_str = uri + "?" + "&".join(params_arr)
        
        # 对 queryStr 进行转码，safe内的保留字符不转换
        encoded_str = urllib.parse.quote(query_str, safe="/:=&?#+!$,;'@()*[]")
        
        # 追加 SK
        raw_str = encoded_str + sk
        
        # 计算 SN
        sn = hashlib.md5(urllib.parse.quote_plus(raw_str).encode("utf8")).hexdigest()
        return sn

    def fetch(self, city_id: str) -> Dict:
        """
        抓取百度天气数据
        
        策略:
        1. 优先使用 district_id (即 city_id/MongoDB _id, 6位代码)
        2. 失败后回退使用 district (即 city_name)
        
        参数:
            city_id: 城市唯一标识符 (MongoDB _id, 通常为6位行政区划代码)
        """
        # 0. 获取城市名称 (用于回退策略)
        city_doc = self.key_manager.db.cities.find_one({"_id": city_id})
        if not city_doc:
            raise Exception(f"City not found for id: {city_id}")
        city_name = city_doc.get("name")

        while True:
            # 1. 从 KeyManager 获取一个可用 Key (格式: ak|sk)
            key_str = self.key_manager.get_key(self.CHANNEL_NAME)
            if not key_str:
                raise Exception(f"No available keys for channel: {self.CHANNEL_NAME}")

            # 解析 AK 和 SK
            if "|" in key_str:
                ak, sk = key_str.split("|")
            else:
                # 兼容旧格式或无 SK 的情况 (虽然现在要求 SN)
                ak = key_str
                sk = ""
                logger.warning(f"[{self.CHANNEL_NAME}] Key 格式警告: {key_str} (缺少 SK，可能导致校验失败)")

            # 定义请求函数
            def do_request(query_params):
                # 构造基础参数
                params = {
                    "data_type": "all",
                    "ak": ak,
                }
                params.update(query_params)
                
                # 计算 SN (如果存在 SK)
                if sk:
                    sn = self.calculate_sn(params, sk)
                    params["sn"] = sn
                
                # 发送请求
                # 注意: requests.get(params=...) 会自动 urlencode，可能会改变参数顺序
                # 导致服务端计算的 SN 与我们计算的不一致
                # 为了稳妥，我们应该自己构建 url
                
                # 复用 calculate_sn 中的逻辑构建最终 URL
                # 但 calculate_sn 只返回 sn，我们需要构建带 sn 的完整 url
                # 这里稍微冗余一点，确保万无一失
                
                # 重新整理:
                # 1. 构建 params 字典 (含 sn)
                # 2. 传给 requests.get(url, params=params)
                # 风险: requests 可能会重新排序参数
                
                # 方案 B: 手动构建 URL
                # host = "https://api.map.baidu.com"
                # final_url = host + query_str + "&sn=" + sn (如果 sk 存在)
                # requests.get(final_url) 会再次编码吗？如果不传 params，requests 会把 url 当作完整 url
                # 但 url 中包含中文等特殊字符时，requests 会自动编码
                
                # 让我们信任 requests，但前提是 calculate_sn 必须基于 requests 最终发送的顺序
                # 这很难控制。
                # 所以最好的办法是：完全手动构建 query string，并手动编码，然后拼接到 url
                
                # 简化版: 既然示例代码都给了，就按示例代码逻辑来
                # 示例最后: url = host + queryStr (含 sn)
                # response = requests.get(url)
                
                host = "https://api.map.baidu.com"
                # 重新构建 queryStr (含 sn)
                # 注意: calculate_sn 里的 query_str 是不含 sn 的
                
                # 为了避免重复代码，我们在 do_request 里直接写逻辑
                
                # 1. 准备参数列表 (有序)
                p_list = []
                p_list.append(f"district_id={query_params.get('district_id', '')}") if 'district_id' in query_params else None
                p_list.append(f"district={query_params.get('district', '')}") if 'district' in query_params else None
                p_list.append("data_type=all")
                p_list.append(f"ak={ak}")
                
                # 过滤空值 (如果有)
                p_list = [p for p in p_list if not p.endswith('=')]
                
                # 2. 拼接
                # uri = "/weather/v1/"
                # query_str_no_sn = uri + "?" + "&".join(p_list)
                
                # 3. 计算 SN
                # encoded_str = urllib.parse.quote(query_str_no_sn, safe="/:=&?#+!$,;'@()*[]")
                # raw_str = encoded_str + sk
                # sn = hashlib.md5(urllib.parse.quote_plus(raw_str).encode("utf8")).hexdigest()
                
                # 4. 最终 URL
                # final_query_str = query_str_no_sn + "&sn=" + sn
                # final_url = host + final_query_str
                
                # 上面的 p_list 构造太硬编码了。
                # 还是用字典吧，Python 3.7+ 字典有序
                
                req_params = query_params.copy()
                req_params["data_type"] = "all"
                req_params["ak"] = ak
                
                # 计算 SN
                sn = ""
                if sk:
                    sn = self.calculate_sn(req_params, sk)
                
                # 构造最终 URL
                # 必须保证顺序与 calculate_sn 一致
                q_parts = []
                for k in req_params:
                    q_parts.append(f"{k}={req_params[k]}")
                
                q_str = "/weather/v1/?" + "&".join(q_parts)
                if sn:
                    q_str += f"&sn={sn}"
                    
                final_url = "https://api.map.baidu.com" + q_str
                
                # 发送请求
                return requests.get(final_url, timeout=5).json()

            try:
                # 策略 1: 使用 district_id (city_id)
                logger.info(f"[{self.CHANNEL_NAME}] 正在使用 district_id {city_id} 抓取 {city_name} (Key: {ak})...")
                data = do_request({"district_id": city_id})
                
                # 检查结果
                if data.get("status") != 0:
                    # 失败，检查是否需要回退
                    # 百度 API 错误码: 
                    # 2xx: 权限问题 -> 换 Key
                    # 3xx: 配额问题 -> 换 Key
                    # other: 参数问题?
                    
                    status = data.get("status")
                    msg = data.get("message", "")
                    logger.warning(f"[{self.CHANNEL_NAME}] district_id {city_id} 失败: {status} - {msg}")
                    
                    # 如果是 Key 相关错误，直接换 Key，不尝试 fallback
                    if status == 302:
                         logger.error(f"[{self.CHANNEL_NAME}] Key {ak} 配额耗尽")
                         self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, until_midnight=True)
                         continue
                    elif status in [200, 210, 211, 220, 240, 250, 251, 252, 301]:
                         logger.error(f"[{self.CHANNEL_NAME}] Key {ak} 权限/认证错误")
                         self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, duration=86400)
                         continue
                    
                    # 策略 2: 使用 district (名称)
                    logger.info(f"[{self.CHANNEL_NAME}] 尝试回退到 district {city_name}...")
                    data = do_request({"district": city_name})
                    
                    if data.get("status") != 0:
                        status = data.get("status")
                        msg = data.get("message", "")
                        logger.warning(f"[{self.CHANNEL_NAME}] district {city_name} 也失败: {status} - {msg}")
                        
                        # 再次检查 Key 错误
                        if status == 302:
                             logger.error(f"[{self.CHANNEL_NAME}] Key {ak} 配额耗尽")
                             self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, until_midnight=True)
                             continue
                        elif status in [200, 210, 211, 220, 240, 250, 251, 252, 301]:
                             logger.error(f"[{self.CHANNEL_NAME}] Key {ak} 权限/认证错误")
                             self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str, duration=86400)
                             continue
                        
                        # 彻底失败
                        logger.error(f"[{self.CHANNEL_NAME}] 城市未找到 (ID & 名称均失败): {city_name}/{city_id}")
                        # 抛出异常或返回空数据?
                        # 这里选择抛出异常，让上层处理
                        raise Exception(f"Baidu API failed for {city_name}: {msg}")

                return data

            except requests.RequestException as e:
                logger.error(f"网络错误 (Key: {ak}): {e}")
                self.key_manager.mark_invalid(self.CHANNEL_NAME, key_str)
                continue

    def normalize(self, raw_data: Dict) -> List[StandardDailyWeather]:
        """
        数据清洗与标准化
        将百度 API 的原始 JSON 数据转换为 StandardDailyWeather 对象列表
        
        参数:
            raw_data: fetch 方法返回的原始数据
            
        返回:
            List[StandardDailyWeather]: 标准化后的天气预报列表
        """
        results = []
        # 提取预报列表，注意判空
        forecasts = raw_data.get("result", {}).get("forecasts", [])

        for item in forecasts:
            # 提取并映射字段
            date = item.get("date")
            temp_high = item.get("high")
            temp_low = item.get("low")
            weather_day = item.get("text_day")
            weather_night = item.get("text_night")
            if item.get("wc_day")==item.get("wc_night"):
                wind_scale = item.get("wc_day") # 假设字段: 白天风向
            else:
                wind_scale=item.get("wc_day")+"-"+item.get("wc_night")
            
            if item.get("wd_day")==item.get("wd_night"):
                wind_direction = item.get("wd_day")     # 假设字段: 白天风力
            else:
                wind_direction=item.get("wd_day")+"-"+item.get("wd_night")
            
            # 特殊处理: 百度 API 可能不直接返回湿度，使用默认值 0
            humidity = 0 
            
            # 构建标准模型对象
            weather = StandardDailyWeather(
                date=date,
                temp_high=int(temp_high),
                temp_low=int(temp_low),
                weather_day=weather_day,
                weather_night=weather_night,
                humidity=humidity,
                wind_direction=wind_direction,
                wind_scale=wind_scale,
                lifestyle=[] # 暂不处理生活指数，设为空列表
            )
            results.append(weather)
            
        return results
