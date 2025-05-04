from datetime import datetime

from celery import Celery

from source.notifications.celery import celery_app
from source.database.models.accounts import ActivationTokenModel
from source.database.session_sqlite import AsyncSQLiteSessionLocal

app = Celery("tasks", backend="redis://localhost", broker="redis://localhost")


@celery_app.task()
def delete_expired_activation_tokens():
    db = AsyncSQLiteSessionLocal
    try:
        expired_activation_tokens = db.query(ActivationTokenModel).filter(ActivationTokenModel.expires_at < datetime.now(datetime.timezone.utc)).all()
        for token in expired_activation_tokens:
            db.delete(token)
        
        db.commit()
    except Exception:
        db.rollback()
        print(f"Error during expired token: {Exception}")
    finally:
        db.close()
