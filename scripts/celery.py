from celery import Celery
import os


redis_host = os.environ.get("REDIS_HOST", "redis")
redis_port = os.environ.get("REDIS_PORT", 6379)

app = Celery(
    "scripts",
    broker=f"redis://{redis_host}:{redis_port}",
    backend=f"redis://{redis_host}:{redis_port}",
    result_backend=f"redis://{redis_host}:{redis_port}",
    result_extended=True,
    include=["satpy_pygeoapi_plugin.process_netcdf"],
)

app.conf.update(
    result_expires=3600,
)

if __name__ == "__main__":
    # Optional configuration, see the application user guide.
    app.start()
