from celery import shared_task
from finquery_app.application.services.query_service import FinQueryService

@shared_task
def process_query_task(user_query):
    service = FinQueryService()
    result = service.process_query(user_query)
    return result
