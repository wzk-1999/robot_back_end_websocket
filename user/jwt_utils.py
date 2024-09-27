import jwt
from django.conf import settings

class JWTUtils:
    @staticmethod
    def extract_jwt_from_cookies(headers):
        """
        Extract JWT token from the cookies in the headers.
        :param headers: The headers dictionary from the WebSocket scope.
        :return: The JWT token string if found, otherwise None.
        """
        if b'cookie' in headers:
            cookies = headers[b'cookie'].decode().split('; ')
            for cookie in cookies:
                if cookie.startswith('jwt='):
                    return cookie.split('=')[1]
        return None

    @staticmethod
    def decode_jwt(token):
        """
        Decode a JWT token using the app's secret key.
        :param token: The JWT token string.
        :return: Decoded token payload if valid, otherwise None.
        :raises: jwt.ExpiredSignatureError, jwt.InvalidTokenError for invalid tokens.
        """
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError:
            raise jwt.InvalidTokenError("Invalid token")
