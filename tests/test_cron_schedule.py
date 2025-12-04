import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_load_beat_schedule():
    # Mock DB return values
    mock_configs = [
        {
            "_id": "single_cron",
            "cron": "0 12 * * *",
            "is_active": True
        },
        {
            "_id": "multi_cron",
            "cron": ["0 7 * * *", "0 8 * * *"],
            "is_active": True
        },
        {
            "_id": "invalid_cron",
            "cron": "invalid",
            "is_active": True
        }
    ]

    # Mock get_db
    with patch("app.celery_app.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_db.channel_configs.find.return_value = mock_configs
        mock_get_db.return_value = mock_db

        # Import the function to test
        # Note: We need to import inside the patch context or reload the module if it was already imported
        from app.celery_app import load_beat_schedule
        
        schedule = load_beat_schedule()
        
        print("Generated Schedule Keys:", schedule.keys())
        
        # Assertions
        assert "update_single_cron" in schedule
        assert "update_multi_cron_0" in schedule
        assert "update_multi_cron_1" in schedule
        assert "update_invalid_cron" not in schedule
        
        print("Test Passed!")

if __name__ == "__main__":
    test_load_beat_schedule()
