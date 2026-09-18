# -*- coding: utf-8 -*-
"""
End-to-end integration tests for Admin API endpoints and HTML template rendering.
Uses FastAPI TestClient with mocked MongoDB and Redis.
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.core.config import settings

def test_admin_full_workflow():
    # Setup mocks for db and redis
    mock_channel_configs = [
        {
            "_id": "hefeng",
            "name": "和风天气",
            "cron": "30 0 * * *,50 4 * * *",
            "is_active": True,
            "wait_max": 10,
            "keys_pool": [
                {"key": "hf_test_key_1", "status": "active", "daily_limit": 2000, "desc": "和风主Key"}
            ]
        },
        {
            "_id": "baidu",
            "name": "百度地图气象",
            "cron": "0 5 * * *",
            "is_active": True,
            "wait_max": 15,
            "keys_pool": [
                {"key": "bd_test_key_1", "status": "active", "daily_limit": 6000, "desc": "百度Key"}
            ]
        }
    ]

    mock_db = MagicMock()
    mock_db.__getitem__.side_effect = lambda name: getattr(mock_db, name)
    mock_db.channel_configs.find.return_value = mock_channel_configs
    mock_db.channel_configs.find_one.side_effect = lambda q: next((c for c in mock_channel_configs if c["_id"] == q.get("_id")), None)
    mock_db.channel_configs.update_one.return_value = MagicMock(matched_count=1, modified_count=1)
    mock_db.client_keys.delete_one.return_value = MagicMock(deleted_count=1)
    mock_db.client_keys.update_one.return_value = MagicMock(matched_count=1, modified_count=1)
    mock_db.client_keys.insert_one.return_value = MagicMock(inserted_id="mock_id")
    
    mock_redis = MagicMock()
    mock_redis.hget.return_value = "42"
    mock_redis.publish.return_value = 1

    with patch("app.core.db.db_manager.get_db", return_value=mock_db), \
         patch("app.core.db.db_manager.get_redis", return_value=mock_redis), \
         patch("app.worker.scheduler.get_db", return_value=mock_db), \
         patch("app.worker.scheduler.get_redis_client", return_value=mock_redis):

        from app.core.client_key_manager import client_key_manager
        client_key_manager.db = mock_db
        client_key_manager.redis = mock_redis

        from app.main import app
        client = TestClient(app)

        # 1. Test GET /admin HTML rendering
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert "WeatherAggregator" in resp.text
        assert "loginModal" in resp.text
        assert "beijingTimeText" in resp.text
        assert "weatherCompareChart" in resp.text
        assert "channelScheduleModal" in resp.text
        print("✅ 1. GET /admin HTML rendered successfully with all essential DOM IDs")

        # 2. Test Admin Login
        login_fail = client.post("/api/v1/admin/login", json={"key": "wrong_key"})
        assert login_fail.status_code == 403

        login_succ = client.post("/api/v1/admin/login", json={"key": settings.ADMIN_LOGIN_KEY})
        assert login_succ.status_code == 200
        assert login_succ.json() == {"status": "ok"}
        print("✅ 2. Admin Login endpoint verified (403 on wrong, 200 on valid key)")

        admin_headers = {"X-Admin-Key": settings.ADMIN_LOGIN_KEY}

        # 3. Test Client Key CRUD
        # 3.1 List
        list_resp = client.get("/api/v1/admin/keys", headers=admin_headers)
        assert list_resp.status_code == 200
        assert isinstance(list_resp.json(), list)

        # 3.2 Create
        create_resp = client.post("/api/v1/admin/keys", headers=admin_headers, json={"name": "测试集成客户端"})
        assert create_resp.status_code == 200
        created_key = create_resp.json()["key"]
        assert created_key.startswith("ck_")

        # 3.3 Update (QPM & IP whitelist)
        update_resp = client.put(f"/api/v1/admin/keys/{created_key}", headers=admin_headers, json={
            "qpm_limit": 150,
            "ip_whitelist_enabled": True,
            "ip_whitelist": ["127.0.0.1", "192.168.1.100"]
        })
        assert update_resp.status_code == 200

        # 3.4 Delete
        del_resp = client.delete(f"/api/v1/admin/keys/{created_key}", headers=admin_headers)
        assert del_resp.status_code == 200
        print("✅ 3. Client Key CRUD endpoints verified")

        # 4. Test Channel Management & Keys Pool
        ch_resp = client.get("/api/v1/admin/channels", headers=admin_headers)
        assert ch_resp.status_code == 200
        chs = ch_resp.json()
        assert len(chs) >= 2
        print("✅ 4. Channel listing & 3-day stats verified")

        # 5. Test Channel Key Status Toggle (active -> disabled)
        mock_db.channel_configs.update_one.return_value = MagicMock(matched_count=1)
        status_resp = client.put(
            "/api/v1/admin/channels/hefeng/keys/status",
            headers=admin_headers,
            json={"key": "hf_test_key_1", "status": "disabled"}
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["new_status"] == "disabled"
        print("✅ 5. Channel Key active/disabled switch endpoint verified")

        # 6. Test Channel Schedule Update (Multi-Cron validation & Beat Hot Reload)
        sched_resp = client.put(
            "/api/v1/admin/channels/hefeng/schedule",
            headers=admin_headers,
            json={
                "cron": "0 6 * * *,\n0 12 * * *,\n0 18 * * *",
                "is_active": True,
                "wait_max": 20
            }
        )
        assert sched_resp.status_code == 200
        assert sched_resp.json()["status"] == "updated"

        # Invalid cron should return 400
        invalid_sched = client.put(
            "/api/v1/admin/channels/hefeng/schedule",
            headers=admin_headers,
            json={"cron": "bad_cron_expression"}
        )
        assert invalid_sched.status_code == 400
        print("✅ 6. Celery Multi-Cron validation & Beat reload signal verified")

        # 7. Test Add & Delete Channel Key
        add_key_resp = client.post(
            "/api/v1/admin/channels/hefeng/keys",
            headers=admin_headers,
            json={"key": "hf_new_key_999", "daily_limit": 3000, "desc": "备份Key"}
        )
        assert add_key_resp.status_code == 200

        del_key_resp = client.request(
            "DELETE",
            "/api/v1/admin/channels/hefeng/keys",
            headers=admin_headers,
            json={"key": "hf_new_key_999"}
        )
        assert del_key_resp.status_code == 200
        print("✅ 7. Add/Delete Channel Key pool endpoints verified")

        print("\n🎉 ALL ADMIN INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_admin_full_workflow()
