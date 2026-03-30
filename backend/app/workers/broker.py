from __future__ import annotations

from app.core.settings import get_settings


def broker_available() -> bool:
    try:
        import dramatiq  # noqa: F401
        from dramatiq.brokers.redis import RedisBroker  # noqa: F401

        return True
    except Exception:
        return False


def get_broker():
    if not broker_available():
        return None

    import dramatiq
    from dramatiq.brokers.redis import RedisBroker

    settings = get_settings()
    broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(broker)
    return broker


def enqueue_execution_job(job_id: str, payload: dict, user_id: str) -> bool:
    if get_broker() is None:
        return False

    try:
        from app.workers.tasks import execute_code_job

        execute_code_job.send(job_id, payload, user_id)
        return True
    except Exception:
        return False


def main() -> None:
    settings = get_settings()
    if broker_available():
        get_broker()
        print(f"Dramatiq broker configured against {settings.redis_url}")
        return

    print(
        "Dramatiq is not installed in this interpreter. "
        "Queued execution will fall back to local threads."
    )


if __name__ == "__main__":
    main()
