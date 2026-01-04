from typing import Optional, Dict
from pymongo.database import Database

class CityManager:
    """
    城市信息管理器
    负责城市信息的查询和解析 (Adcode <-> City Name)
    """
    def __init__(self, db: Database):
        """
        初始化 CityManager
        
        参数:
            db: MongoDB 数据库实例
        """
        self.db = db

    def resolve_city(self, identifier: str) -> Optional[Dict]:
        """
        解析城市信息
        支持通过 Adcode 或 城市名称 查询城市详情
        
        参数:
            identifier: 城市标识符 (Adcode 如 '110105' 或 名称 如 '朝阳区')
            
        返回:
            Optional[Dict]: 城市文档字典，未找到返回 None
        """
        # 1. 首次查询：精确匹配 (不包含模糊查询,避免误匹配)
        query = {
            "$or": [
                {"_id": identifier},
                {"name": identifier},
                {"adcode": identifier}
            ]
        }
        result = self.db.cities.find_one(query)
        
        if result:
            return result
            
        # 2. 重试机制：去除后缀后重试
        # 场景：用户输入 "北京市"，数据库存的是 "北京"
        search_city_name = identifier
        if len(search_city_name) >= 2:
            for suffix in ["市", "区", "县", "省"]:
                if search_city_name.endswith(suffix):
                    search_city_name = search_city_name[:-1]
                    break
            
            # 2.1 先用去除后缀的完整名称精确查询
            if search_city_name != identifier:
                retry_query = {"name": search_city_name}
                result = self.db.cities.find_one(retry_query)
                if result:
                    return result
            
            # 2.2 如果精确查询仍失败,再进行模糊查询
            fuzzy_query = {"name": {"$regex": f"^{search_city_name}"}}
            return self.db.cities.find_one(fuzzy_query)
                 
        return None

from app.core.db import get_db
city_manager = CityManager(get_db())
