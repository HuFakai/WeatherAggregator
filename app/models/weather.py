from typing import List, Dict, Optional
from pydantic import BaseModel, Field

# 1. 生活指数模型 (嵌套对象)
class LifestyleIndex(BaseModel):
    """
    生活指数数据模型
    用于描述穿衣、运动等生活建议
    """
    title: str = Field(..., description="指数名称，如穿衣、运动")
    level: str = Field(..., description="等级，如适宜、较差")
    desc: str = Field(..., description="详细建议描述")

# 2. 单日标准天气模型 (全量字段)
class StandardDailyWeather(BaseModel):
    """
    标准化的单日天气预报模型
    所有渠道抓取的数据都必须转换为此格式
    """
    date: str = Field(..., description="日期，格式 YYYY-MM-DD")
    
    # 温度信息 (拆分为高温和低温)
    temp_high: int = Field(..., description="最高气温 (摄氏度)")
    temp_low: int = Field(..., description="最低气温 (摄氏度)")
    
    # 天气状况 (拆分为白天和夜间)
    weather_day: str = Field(..., description="白天天气现象 (如: 晴/多云/雨)")
    weather_night: str = Field(..., description="夜间天气现象")
    
    # 详细气象指标
    humidity: int = Field(default=0, description="相对湿度，百分比 0-100。若源数据缺失默认为 0")
    wind_direction: str = Field(..., description="风向 (如: 东南风)")
    wind_scale: str = Field(..., description="风力等级 (如: 3-4级)")
    
    # 空气质量 (可选字段，部分渠道可能无数据)
    aqi: Optional[int] = Field(None, description="空气质量指数 (AQI)")
    aqi_level: Optional[str] = Field(None, description="空气质量等级 (如: 良/轻度污染)")
    
    # 生活指数列表
    lifestyle: List[LifestyleIndex] = Field(default_factory=list, description="生活指数列表，默认为空")

# 3. 数据库文档模型
class WeatherRecord(BaseModel):
    """
    MongoDB 存储的天气记录模型
    按城市聚合不同渠道的天气数据
    """
    id: str = Field(alias="_id", description="城市代码 (Adcode)，作为主键")
    city_name: str = Field(..., description="城市名称")
    last_updated_at: str = Field(..., description="最后更新时间 (ISO 格式)")
    
    # 数据源字典
    # Key: 渠道名称 (如 'baidu', 'amap')
    # Value: 该渠道对应的未来天气预报列表
    sources: Dict[str, List[StandardDailyWeather]] = Field(default_factory=dict, description="各渠道的天气数据集合")
