from abc import ABC, abstractmethod
from typing import List, Dict
from app.core.key_manager import RandomKeyManager
from app.models.weather import StandardDailyWeather

class BaseFetcher(ABC):
    """
    天气抓取器抽象基类
    定义了所有具体渠道抓取器 (Fetcher) 必须实现的接口
    """
    
    def __init__(self, key_manager: RandomKeyManager):
        """
        初始化 BaseFetcher
        
        参数:
            key_manager: Key 管理器实例，用于获取 API Key
        """
        self.key_manager = key_manager

    @abstractmethod
    def fetch(self, city_code: str) -> Dict:
        """
        抽象方法: 抓取天气数据
        
        参数:
            city_code: 城市代码 (Adcode)
            
        返回:
            Dict: 原始 API 响应数据
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: Dict) -> List[StandardDailyWeather]:
        """
        抽象方法: 标准化天气数据
        将原始 API 响应转换为系统统一的 StandardDailyWeather 模型列表
        
        参数:
            raw_data: 原始 API 响应数据
            
        返回:
            List[StandardDailyWeather]: 标准化后的天气预报列表
        """
        pass
