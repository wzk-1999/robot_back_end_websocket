# views.py
from django.http import JsonResponse
from .redisUtils import RedisUtils

async def get_recent_messages_view(request):
    user_id = request.session.get('temp_user_id')
    if not user_id:
        return JsonResponse({'error': 'User ID not found'}, status=400)

    messages = await RedisUtils.get_messages(user_id)
    return JsonResponse({'messages': messages})
