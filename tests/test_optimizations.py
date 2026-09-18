import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.key_manager import KeyManager
from app.core.client_key_manager import ClientKeyManager
from app.celery_app import celery_app

class TestOptimizations(unittest.TestCase):

    def test_database_settings_direct(self):
        """验证数据库配置为直连配置，无 SSH 字段"""
        self.assertFalse(hasattr(settings, "SSH_HOST"))
        self.assertFalse(hasattr(settings, "SSH_PORT"))
        self.assertTrue(hasattr(settings, "MONGO_HOST"))
        self.assertTrue(hasattr(settings, "REDIS_HOST"))

    def test_celery_task_ignore_result(self):
        """验证 Celery 配置中开启了 task_ignore_result，防止 Redis 元数据堆积"""
        self.assertTrue(celery_app.conf.task_ignore_result)

    def test_key_manager_timedelta_and_pipeline(self):
        """验证 KeyManager delete_key_stats 与 record_usage 正常工作"""
        mock_db = MagicMock()
        mock_redis = MagicMock()
        pipe_mock = MagicMock()
        mock_redis.pipeline.return_value = pipe_mock

        km = KeyManager(mock_db, mock_redis)
        
        # 1. 验证 record_usage
        km.record_usage("baidu", "test_key")
        pipe_mock.hincrby.assert_called_once()
        pipe_mock.expire.assert_called_once()
        pipe_mock.execute.assert_called_once()

        # 2. 验证 delete_key_stats 导入了 timedelta 且不抛异常
        pipe_mock.reset_mock()
        km.delete_key_stats("baidu", "test_key")
        self.assertEqual(pipe_mock.hdel.call_count, 4)
        pipe_mock.delete.assert_called_once()
        pipe_mock.execute.assert_called_once()

    def test_client_key_manager_qpm_pipeline(self):
        """验证 client_key_manager validate_access 速率限制使用 pipeline 设置 expire"""
        with patch("app.core.client_key_manager.db_manager") as mock_dbm:
            mock_db = MagicMock()
            mock_redis = MagicMock()
            pipe_mock = MagicMock()
            mock_redis.pipeline.return_value = pipe_mock
            mock_dbm.get_db.return_value = mock_db
            mock_dbm.get_redis.return_value = mock_redis

            # Mock client key doc
            mock_db["client_keys"].find_one.return_value = {
                "key": "ck_test123",
                "name": "Test Key",
                "ip_whitelist_enabled": False,
                "ip_whitelist": [],
                "qpm_limit": 10,
                "created_at": datetime.now()
            }
            pipe_mock.execute.return_value = [1]  # current_count = 1

            ckm = ClientKeyManager()
            is_valid, msg = ckm.validate_access("ck_test123", "127.0.0.1")
            self.assertTrue(is_valid)
            self.assertEqual(msg, "")
            pipe_mock.incr.assert_called_once()
            pipe_mock.expire.assert_called_once()
            pipe_mock.execute.assert_called_once()

    def test_client_key_rename_and_redis_migration(self):
        """验证 ClientKey 修改密钥值及 Redis 统计平滑迁移"""
        with patch("app.core.client_key_manager.db_manager") as mock_dbm:
            mock_db = MagicMock()
            mock_redis = MagicMock()
            mock_dbm.get_db.return_value = mock_db
            mock_dbm.get_redis.return_value = mock_redis

            old_key = "ck_original"
            new_key = "ck_customized"

            # 模拟现有数据库查询
            def find_one_side_effect(query):
                if query.get("key") == old_key:
                    return {"key": old_key, "name": "App Client", "qpm_limit": 5}
                if query.get("key") == new_key:
                    return None  # 新 key 未被占用
                return None
            mock_db["client_keys"].find_one.side_effect = find_one_side_effect
            mock_db["client_keys"].update_one.return_value = MagicMock(matched_count=1)

            # 模拟 Redis 读写 pipeline
            read_pipe = MagicMock()
            read_pipe.execute.return_value = [b"100", 50000] * 8  # 8 天的读结果
            write_pipe = MagicMock()
            mock_redis.pipeline.side_effect = [read_pipe, write_pipe]

            ckm = ClientKeyManager()
            success, err_msg = ckm.update_key(old_key, {"qpm_limit": 10}, new_key=new_key)
            self.assertTrue(success)
            self.assertEqual(err_msg, "")

            # 检查 MongoDB 更新内容包含新 key
            mock_db["client_keys"].update_one.assert_called_once()
            args, kwargs = mock_db["client_keys"].update_one.call_args
            self.assertEqual(args[0], {"key": old_key})
            self.assertEqual(args[1]["$set"]["key"], new_key)
            self.assertEqual(args[1]["$set"]["qpm_limit"], 10)

            # 检查 Redis 迁移调用
            write_pipe.setex.assert_called()
            write_pipe.delete.assert_called()
            write_pipe.execute.assert_called_once()

    def test_client_key_rename_duplicate_rejected(self):
        """验证修改为已存在的密钥值时被拒绝"""
        with patch("app.core.client_key_manager.db_manager") as mock_dbm:
            mock_db = MagicMock()
            mock_dbm.get_db.return_value = mock_db
            mock_dbm.get_redis.return_value = MagicMock()

            old_key = "ck_original"
            new_key = "ck_already_exists"

            # 模拟新 key 已存在
            mock_db["client_keys"].find_one.return_value = {"key": new_key}

            ckm = ClientKeyManager()
            success, err_msg = ckm.update_key(old_key, {}, new_key=new_key)
            self.assertFalse(success)
            self.assertIn("已存在", err_msg)

    def test_fetcher_registry(self):
        """验证 FetcherRegistry 注册与工厂获取机制"""
        from app.worker.fetchers.registry import FetcherRegistry
        from app.worker.fetchers.hefeng import HeFengFetcher
        from app.worker.fetchers.yike import YiKeFetcher
        from app.worker.fetchers.baidu import BaiduFetcher

        mock_db = MagicMock()
        mock_redis = MagicMock()

        # 验证获取 Fetcher 实例
        self.assertIsInstance(FetcherRegistry.get_fetcher("hefeng", db=mock_db, redis_client=mock_redis), HeFengFetcher)
        self.assertIsInstance(FetcherRegistry.get_fetcher("yiketianqi", db=mock_db, redis_client=mock_redis), YiKeFetcher)
        self.assertIsInstance(FetcherRegistry.get_fetcher("baidu", db=mock_db, redis_client=mock_redis), BaiduFetcher)
        self.assertIsNone(FetcherRegistry.get_fetcher("unknown_channel"))

        # 验证获取 Fetcher 类
        self.assertIs(FetcherRegistry.get_fetcher_class("hefeng"), HeFengFetcher)
        self.assertIs(FetcherRegistry.get_fetcher_class("yiketianqi"), YiKeFetcher)
        self.assertIs(FetcherRegistry.get_fetcher_class("baidu"), BaiduFetcher)

        all_channels = FetcherRegistry.list_supported_channels()
        self.assertIn("hefeng", all_channels)
        self.assertIn("yiketianqi", all_channels)
        self.assertIn("baidu", all_channels)



    @patch("app.worker.scheduler.get_redis_client")
    @patch("app.worker.scheduler.get_db")
    def test_dynamic_mongo_scheduler(self, mock_get_db, mock_get_redis):
        """验证 DynamicMongoScheduler 动态从 Mongo 加载并根据 Redis 信号热刷新"""
        from app.worker.scheduler import DynamicMongoScheduler

        mock_db = MagicMock()
        mock_redis = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_redis.return_value = mock_redis

        # 模拟 Mongo 返回渠道数据
        mock_db.channel_configs.find.return_value = [
            {"_id": "hefeng", "cron": "*/10 * * * *", "is_active": True},
            {"_id": "yiketianqi", "cron": "0 * * * *", "is_active": True},
        ]
        mock_redis.get.return_value = b"flag_v1"

        scheduler = DynamicMongoScheduler(app=celery_app)

        # 执行 setup_schedule
        scheduler.setup_schedule()

        self.assertIn("update_hefeng", scheduler.schedule)
        self.assertIn("update_yiketianqi", scheduler.schedule)

        # 模拟心跳检测：mock super().tick 避免真正调度队列计算
        with patch("celery.beat.Scheduler.tick", return_value=5.0):
            # 信号未变，不重新读取 Mongo
            mock_db.channel_configs.find.reset_mock()
            mock_redis.get.return_value = b"flag_v1"
            scheduler._last_check_time = 0
            scheduler.tick()
            mock_db.channel_configs.find.assert_not_called()

            # 模拟信号变为 flag_v2：触发热重载，并且 yiketianqi 变为停用
            mock_redis.get.return_value = b"flag_v2"
            mock_db.channel_configs.find.return_value = [
                {"_id": "hefeng", "cron": "*/10 * * * *", "is_active": True}
            ]
            scheduler._last_check_time = 0
            scheduler.tick()

            mock_db.channel_configs.find.assert_called_once()
            self.assertIn("update_hefeng", scheduler.schedule)
            self.assertNotIn("update_yiketianqi", scheduler.schedule)



    def test_weather_endpoint_router_definitions(self):
        """验证天气路由定义同时包含路径传参与根路径查询传参"""
        from app.api.v1.endpoints.weather import router

        routes = {route.path: route for route in router.routes}
        self.assertIn("", routes)
        self.assertIn("/{city}", routes)

    def test_weather_endpoint_path_and_query_functions(self):
        """测试 get_weather_by_query 与 get_weather_by_path 路由函数参数校验与转发"""
        import asyncio
        from fastapi import HTTPException
        from app.api.v1.endpoints.weather import get_weather_by_query, get_weather_by_path
        from unittest.mock import AsyncMock

        mock_bg = MagicMock()
        api_key = "test_key"

        # 1. 验证 get_weather_by_query 缺少 city 时抛出 400
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_weather_by_query(background_tasks=mock_bg, city=None, api_key=api_key))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("city", ctx.exception.detail)

        # 2. 验证两者都正确转发给 _get_weather_core
        with patch("app.api.v1.endpoints.weather._get_weather_core", new_callable=AsyncMock) as mock_core:
            mock_core.return_value = {"city_name": "北京", "sources": {}}

            # Query 方式传参
            res_query = asyncio.run(get_weather_by_query(background_tasks=mock_bg, city="北京", api_key=api_key))
            mock_core.assert_called_with("北京", mock_bg, api_key)
            self.assertEqual(res_query["city_name"], "北京")

            # Path 方式传参
            mock_core.reset_mock()
            res_path = asyncio.run(get_weather_by_path(city="上海", background_tasks=mock_bg, api_key=api_key))
            mock_core.assert_called_with("上海", mock_bg, api_key)
            self.assertEqual(res_path["city_name"], "北京")

    def test_timezone_utilities(self):
        """验证 timezone 工具函数产出带有时区感知的北京时间并支持时区安全转换"""
        from app.core.timezone import get_beijing_now, get_beijing_today_str, get_beijing_date, to_beijing_datetime, BEIJING_TZ
        from zoneinfo import ZoneInfo
        from datetime import timezone

        bj_now = get_beijing_now()
        self.assertEqual(bj_now.tzinfo.key, "Asia/Shanghai")
        self.assertEqual(get_beijing_today_str(), bj_now.strftime("%Y-%m-%d"))
        self.assertEqual(get_beijing_date(), bj_now.date())

        # 验证 UTC 转换：UTC 2026-09-18 16:30 -> 北京时间 2026-09-19 00:30
        utc_dt = datetime(2026, 9, 18, 16, 30, tzinfo=timezone.utc)
        converted_bj = to_beijing_datetime(utc_dt)
        self.assertEqual(converted_bj.year, 2026)
        self.assertEqual(converted_bj.month, 9)
        self.assertEqual(converted_bj.day, 19)
        self.assertEqual(converted_bj.hour, 0)
        self.assertEqual(converted_bj.minute, 30)

    def test_celery_timezone_and_enable_utc_false(self):
        """验证 Celery 配置中时区为 Asia/Shanghai 且 enable_utc 为 False"""
        self.assertEqual(celery_app.conf.timezone, "Asia/Shanghai")
        self.assertFalse(celery_app.conf.enable_utc)

    def test_key_manager_uses_beijing_date(self):
        """验证 KeyManager.record_usage 使用北京时间作为 Redis 键的日期"""
        from app.core.timezone import get_beijing_today_str

        mock_db = MagicMock()
        mock_redis = MagicMock()
        pipe_mock = MagicMock()
        mock_redis.pipeline.return_value = pipe_mock

        km = KeyManager(mock_db, mock_redis)
        km.record_usage("hefeng", "test_key")

        expected_today = get_beijing_today_str()
        expected_key = f"stats:usage:hefeng:{expected_today}"

        pipe_mock.hincrby.assert_called_once_with(expected_key, "test_key", 1)
        pipe_mock.expire.assert_called_once_with(expected_key, 259200)

    def test_client_key_manager_uses_beijing_date(self):
        """验证 ClientKeyManager.track_usage 使用北京时间作为 Redis 键的日期"""
        from app.core.timezone import get_beijing_today_str

        with patch("app.core.client_key_manager.db_manager") as mock_dbm:
            mock_db = MagicMock()
            mock_redis = MagicMock()
            pipe_mock = MagicMock()
            mock_redis.pipeline.return_value = pipe_mock
            mock_dbm.get_db.return_value = mock_db
            mock_dbm.get_redis.return_value = mock_redis

            ckm = ClientKeyManager()
            ckm.track_usage("ck_test123")

            expected_today = get_beijing_today_str()
            expected_key = f"usage:client:ck_test123:{expected_today}"

            pipe_mock.incr.assert_called_once_with(expected_key)
            pipe_mock.expire.assert_called_once()

if __name__ == "__main__":
    unittest.main()




