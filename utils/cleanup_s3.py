from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import os
from utils.get_s3_client import get_s3_client

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

def cleanup_old_files():
    s3_client = get_s3_client()

    try:
        objects = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME)

        if "Contents" not in objects:
            print("No objects found in bucket")
            return

        current_time = datetime.now(timezone.utc)
        deleted_count = 0

        for obj in objects["Contents"]:
            age = (current_time - obj["LastModified"]).total_seconds() / 60

            MAX_FILE_AGE_MINS = int(os.getenv("MAX_FILE_AGE_MINS"))

            if age > MAX_FILE_AGE_MINS:
                try:
                    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=obj["Key"])
                    deleted_count += 1
                    print(f"Deleted {obj['Key']} (age: {age:.2f} mins)")
                except Exception as e:
                    print(f"Error deleting {obj['Key']}: {str(e)}")

        if deleted_count > 0:
            print(f"Cleanup completed. Deleted {deleted_count} files.")

    except Exception as e:
        print(f"Error during cleanup: {str(e)}")


def init_cleanup_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        cleanup_old_files,
        "interval",
        minutes=int(os.getenv("CLEANUP_INTERVAL")),
        id="cleanup_s3_files",
    )
    scheduler.start()
    print("S3 cleanup scheduler initialized")
    return scheduler
