from app.core.db import db_manager
from app.core.config import settings

def check():
    print(f"Environment: {settings.APP_ENV}")
    db = db_manager.get_db()
    channels = list(db.channel_configs.find())
    print(f"Found {len(channels)} channels")
    for c in channels:
        print(c)

if __name__ == "__main__":
    check()
