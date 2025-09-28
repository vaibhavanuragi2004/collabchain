# accounts/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication

class JWTCookieAuthentication(JWTAuthentication):
    """
    An authentication class that extends JWTAuthentication to read JWT from
    an HttpOnly cookie.
    """
    def authenticate(self, request):
        # Get the token from the cookie
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None

        # The 'authenticate' method of the parent class expects a validated token
        # The 'get_validated_token' method handles the decoding and validation.
        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception as e:
            # Handle exceptions like TokenError, InvalidToken, etc.
            return None