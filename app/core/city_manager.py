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
        # 尝试匹配 _id (Adcode) 或 name (城市名称)
        # 使用 $or 操作符进行多条件查询
        # name 字段使用正则进行模糊匹配 (只要包含 identifier 即可，或者前缀匹配)
        # 用户需求: "数据库中是朝阳区，用户请求的是朝阳" -> 只要 name 包含 identifier
        # 1. 首次尝试查询
        query = {
            "$or": [
                {"_id": identifier},
                {"name": identifier},
                {"adcode": identifier},
                # 模糊查询: name 包含 identifier
                {"name": {"$regex": identifier}}
            ]
        }
        result = self.db.cities.find_one(query)
        
        if result:
            return result
            
        # 2. 重试机制：去除后缀后重试
        # 场景：用户输入 "北京市"，数据库存的是 "北京"
        search_city_name = identifier
        if len(search_city_name) >= 3:
            if search_city_name.endswith("市") or search_city_name.endswith("区") or search_city_name.endswith("县"):
                 search_city_name = search_city_name[:-1]
                 
                 # 使用处理后的名称再次查询
                 retry_query = {
                    "$or": [
                        {"name": search_city_name},
                        {"name": {"$regex": search_city_name}}
                    ]
                 }
                 return self.db.cities.find_one(retry_query)
                 
        return None

from app.core.db import get_db
city_manager = CityManager(get_db())
