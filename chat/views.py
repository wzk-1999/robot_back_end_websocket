# views.py
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .redisUtils import RedisUtils

@csrf_exempt
async def delete_session(request):
    try:
        body = json.loads(request.body)
        session_id = body.get('session_id')

        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)

        # Call the delete method
        await RedisUtils.delete_temp_user_key(session_id)

        return JsonResponse({'message': 'Session deleted successfully'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
