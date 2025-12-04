import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import get_db, close_db

def check_missing_records():
    """
    对比 cities 和 weather_records 集合
    找出 weather_records 中没有记录的城市
    """
    try:
        db = get_db()
        
        print("正在获取所有城市信息...")
        # 获取所有启用的城市
        cities_cursor = db.cities.find({"is_active": True}, {"_id": 1, "name": 1, "adcode": 1})
        all_cities = {c["_id"]: c for c in cities_cursor}
        print(f"总计活跃城市: {len(all_cities)}")
        
        print("正在获取天气记录...")
        # 获取所有天气记录的 ID (即 adcode)
        records_cursor = db.weather_records.find({}, {"_id": 1})
        existing_records = {r["_id"] for r in records_cursor}
        print(f"总计天气记录: {len(existing_records)}")
        
        # 找出缺失的城市
        missing_adcodes = set(all_cities.keys()) - existing_records
        missing_cities = [all_cities[adcode] for adcode in missing_adcodes]
        
        print(f"缺失记录的城市数量: {len(missing_cities)}")
        
        # 保存到 JSON 文件
        output_file = "missing_cities.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(missing_cities, f, ensure_ascii=False, indent=4)
            
        print(f"缺失城市列表已保存至: {output_file}")
        
    except Exception as e:
        print(f"脚本执行出错: {e}")
    finally:
        close_db()

if __name__ == "__main__":
    check_missing_records()
