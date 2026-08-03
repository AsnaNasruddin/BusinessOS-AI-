from app.worker.celery_app import celery_app


@celery_app.task(name="ping")
def ping() -> str:
    """Trivial task proving the worker container boots and can execute
    something — real tasks (execute_workflow, ingest_document, generate_workflow_plan)
    land here in their respective phases."""
    return "pong"
