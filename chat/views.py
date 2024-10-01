# views.py
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from user.jwt_utils import JWTUtils
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

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE')})


async def handle_like(request):
    # Extract JWT from cookies using the utility class
    headers = dict(request.scope['headers'])
    jwt_token = JWTUtils.extract_jwt_from_cookies(headers)

    if jwt_token:
        decoded_token = JWTUtils.decode_jwt(jwt_token)
        user_id = decoded_token.get('email')
        if user_id:
            data = json.loads(request.body)
            message_id = data.get('messageId')
            is_liked = data.get('isLiked')

            if message_id and is_liked is not None:
                # Update the database or Redis here...
                await RedisUtils.update_like_status(user_id, message_id, is_liked)
                # Respond with success
                return JsonResponse({'message': 'like status changed successfully'}, status=200)
            else:
                return JsonResponse({'error in updating like status'}, status=400)
