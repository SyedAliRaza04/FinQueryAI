from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import AccessToken
from django.http import StreamingHttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.core.cache import cache
from finquery_app.tasks import process_query_task
from celery.result import AsyncResult
from finquery_app.models import ChatSession, ChatMessage
from finquery_app.serializers import ChatSessionSerializer, ChatSessionListSerializer, ChatMessageSerializer
import sqlite3
import random
import os
import hashlib
import json
import uuid
import time

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_auth(request):
    """Debug endpoint to verify token authentication."""
    return Response({
        "username": request.user.username,
        "is_authenticated": request.user.is_authenticated,
        "auth_header": request.headers.get('Authorization', 'Missing')
    })

class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for handling Chat Histories
    """
    def get_queryset(self):
        # Enforce data isolation: users can only see their own sessions
        return ChatSession.objects.filter(owner=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatSessionListSerializer
        return ChatSessionSerializer
        
    def perform_create(self, serializer):
        # Link session to the authenticated user
        serializer.save(owner=self.request.user, title="New Conversation")

class QueryViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for handling FinQuery requests.
    """
    
    def list(self, request):
        return Response({"status": "FinQuery API is running. Use POST /api/query/execute/ to run a query."})

    @action(detail=False, methods=['post'])
    def execute(self, request):
        user_query = request.data.get('query')
        session_id = request.data.get('session_id')
        
        if not user_query:
            return Response({"error": "No query provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        if not session_id:
             return Response({"error": "Session ID required"}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
             # Ensure user owns the session they are querying against
             session = ChatSession.objects.get(id=session_id, owner=self.request.user)
        except ChatSession.DoesNotExist:
             return Response({"error": "Invalid Session ID or Access Denied"}, status=status.HTTP_404_NOT_FOUND)
        
        # 1. Save User Message immediately to DB
        ChatMessage.objects.create(
             session=session,
             role='user',
             content=user_query
        )
        
        # Optionally update session title if this is the first message
        if session.messages.count() <= 1:
            title = user_query[:30] + "..." if len(user_query) > 30 else user_query
            session.title = title
            session.save()
        
        # 2. Trigger Celery Task (Modify task later to save the bot response directly to DB)
        task = process_query_task.delay(user_query)
        
        return Response({
            "task_id": task.id,
            "session_id": session_id,
            "status": "Processing",
            "message": "Query has been submitted for processing."
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Check the status of a task by its ID.
        """
        task_id = pk
        session_id = request.query_params.get('session_id')
        task_result = AsyncResult(task_id)
        
        response_data = {
            "task_id": task_id,
            "status": task_result.status,
        }

        if task_result.successful():
            result = task_result.result
            response_data["result"] = result
            
            # If successful and session_id provided, save the assistant message to the DB
            if session_id and request.query_params.get('save', 'true') == 'true':
                 try:
                     # Verify ownership during status poll as well
                     session = ChatSession.objects.get(id=session_id, owner=self.request.user)
                     ChatMessage.objects.create(
                         session=session,
                         role='assistant',
                         content=result.get("summary", "Query completed."),
                         code_snippet=result.get("generated_sql", None),
                         raw_data_json=result.get("raw_data", None)
                     )
                 except Exception as e:
                     print(f"Error saving assistant message: {e}")
                     
        elif task_result.failed():
            response_data["error"] = str(task_result.result)
            
        return Response(response_data)


# Standard Django view to handle SSE and bypass DRF renderer negotiation (prevents 406 errors)
def stream_query(request):
    # Support token in query for EventSource which doesn't support headers easily
    token = request.GET.get('token')
    user = request.user
    
    if token and not user.is_authenticated:
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
        except Exception:
            return JsonResponse({"error": "Invalid Token"}, status=401)

    if not user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
        
    user_query = request.GET.get('query')
    session_id = request.GET.get('session_id')
    
    if not user_query:
        return JsonResponse({"error": "No query provided"}, status=400)
        
    session = None
    if session_id:
        try:
            # Enforce ownership in stream endpoint
            session = ChatSession.objects.get(id=session_id, owner=user)
            if session.messages.count() <= 1:
                title = user_query[:30] + "..." if len(user_query) > 30 else user_query
                session.title = title
                session.save()
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Invalid Session ID or Access Denied"}, status=403)

    # 1. Caching Layer
    query_hash = hashlib.md5(user_query.lower().strip().encode('utf-8')).hexdigest()
    cache_key = f"finquery_result_{query_hash}"
    cached_result = cache.get(cache_key)
    
    if cached_result:
        # We have a cached result! Return it instantly via a fast mock stream 
        def mock_stream():
            yield f"data: {json.dumps({'type': 'status', 'content': 'Cache hit! Retrieving...'})}\n\n"
            
            if session:
                ChatMessage.objects.create(session=session, role='user', content=user_query)
            
            yield f"data: {json.dumps({'type': 'sql', 'content': cached_result.get('sql_query', '')})}\n\n"
            yield f"data: {json.dumps({'type': 'raw_data', 'content': cached_result.get('raw_data', [])})}\n\n"
            yield f"data: {json.dumps({'type': 'reasoning_done', 'content': ''})}\n\n"
            # Single token event — no chunked loop (avoids WSGI buffering)
            summary = cached_result.get('summary', '')
            yield f"data: {json.dumps({'type': 'token', 'content': summary})}\n\n"
            
            if session:
                ChatMessage.objects.create(
                     session=session,
                     role='assistant',
                     content=summary,
                     code_snippet=cached_result.get('sql_query', ''),
                     raw_data_json=cached_result.get('raw_data', [])
                )
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        response = StreamingHttpResponse(mock_stream(), content_type='text/event-stream')
        _set_sse_headers(response)
        return response

    # Cache Miss, run the real generative stream
    if session:
         ChatMessage.objects.create(
             session=session,
             role='user',
             content=user_query
         )
            
    def sse_stream():
        from finquery_app.application.services.query_service import FinQueryService
        service = FinQueryService()
        for event_string in service.process_query_stream(user_query, cache_key=cache_key, session=session):
            yield event_string
            
    response = StreamingHttpResponse(sse_stream(), content_type='text/event-stream')
    _set_sse_headers(response)
    return response


def _set_sse_headers(response: StreamingHttpResponse) -> None:
    """
    Apply headers that prevent proxy/middleware/browser buffering of SSE streams.

    NOTE: 'Connection' is a hop-by-hop header — Django's WSGI server (wsgiref)
    forbids it and raises AssertionError. It is intentionally excluded here.
    In production behind Nginx, X-Accel-Buffering: no handles proxy buffering.
    """
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'   # Disables Nginx proxy buffering
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'


class AnalyticsViewSet(viewsets.ViewSet):
    """
    API endpoint for serving live dashboard metrics directly from the core banking database.
    """
    
    def list(self, request):
        db_path = "bank_customers.db"
        if not os.path.exists(db_path):
             return Response({"error": f"Database {db_path} not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
             
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Total Managed Assets
            cursor.execute("SELECT SUM(balance) FROM investment_accounts")
            total_assets = cursor.fetchone()[0] or 0
            
            # 2. Active Customers
            cursor.execute("SELECT COUNT(*) FROM customers")
            total_customers = cursor.fetchone()[0] or 0
            
            # 3. Active Loans
            cursor.execute("SELECT COUNT(*) FROM loans WHERE status='Active' OR status='Approved'")
            total_loans = cursor.fetchone()[0] or 0
            
            # 4. Total Monthly Transacted (Using sum of all tx for simplicity of PoC, or could filter by recent dates)
            cursor.execute("SELECT SUM(amount) FROM transactions")
            total_tx = cursor.fetchone()[0] or 0
            
            # 5. Top Portfolios
            cursor.execute('''
                SELECT c.customer_name, i.account_type, i.balance 
                FROM investment_accounts i
                JOIN customers c ON i.customer_id = c.customer_id
                ORDER BY i.balance DESC LIMIT 4
            ''')
            top_portfolios_raw = cursor.fetchall()
            
            top_portfolios = []
            for row in top_portfolios_raw:
                top_portfolios.append({
                    "name": row[0],
                    "type": row[1],
                    "amount": f"${row[2]:,.0f}",
                    "ror": f"{'+' if random.random() > 0.3 else '-'}{round(random.uniform(1.0, 15.0), 1)}%" # Simulated RoR for PoC
                })
                
            # 6. Transaction Volume (Simulating 7 months based on DB aggregate to ensure chart variance)
            # In a real app we GROUP BY strftime('%Y-%m', transaction_date). 
            # Here we generate normalized percentages based on total_tx for visual aesthetic
            chart_data = [
                 random.randint(40, 95) for _ in range(7)
            ]
            
            return Response({
                "totalAssets": f"${total_assets / 1000000:.1f}M",
                "activeUsers": f"{total_customers:,}",
                "activeLoans": f"{total_loans:,}",
                "monthlyTx": f"${total_tx / 1000000:.1f}M",
                "topPortfolios": top_portfolios,
                "chartData": chart_data
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            conn.close()
