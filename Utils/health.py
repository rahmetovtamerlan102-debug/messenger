from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache

def health_check(request):
    status = {'status': 'ok', 'components': {}}
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
        status['components']['postgresql'] = 'ok'
    except Exception as e:
        status['components']['postgresql'] = f'error: {str(e)}'
        status['status'] = 'degraded'
    try:
        cache.set('health_check', 1, timeout=1)
        cache.get('health_check')
        status['components']['redis'] = 'ok'
    except Exception as e:
        status['components']['redis'] = f'error: {str(e)}'
        status['status'] = 'degraded'
    return JsonResponse(status)
