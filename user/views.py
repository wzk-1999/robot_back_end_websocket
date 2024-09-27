from datetime import datetime, timedelta
from pytz import timezone

import jwt
# Create your views here.

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from robot_back_end import settings


class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if email:
            # Set timezone to Toronto using pytz
            toronto_tz =timezone('America/Toronto')

            # Get current datetime in Toronto timezone
            current_time = datetime.now(toronto_tz)
            expiration_time = current_time + timedelta(hours=24)

            # Manually create a token payload with timezone-aware datetime
            payload = {
                'email': email,
                'exp': expiration_time.timestamp(),  # Convert expiration to timestamp
                'iat': current_time.timestamp(),  # Convert issued-at time to timestamp
            }

            # Encode token using secret key
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            # # Decode the token to get the expiration timestamp for debugging
            # decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            # exp_timestamp = decoded_token['exp']
            # exp_time = datetime.fromtimestamp(exp_timestamp, toronto_tz)
            #
            # print(f"Token will expire at: {exp_time.isoformat()}")

            return Response({
                'access': token
            })
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

