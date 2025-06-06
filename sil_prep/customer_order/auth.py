from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.exceptions import AuthenticationFailed
from oauthlib.oauth2 import Server
from oauth2_provider.oauth2_validators import OAuth2Validator

class OIDCAuthentication(OAuth2Authentication):
    def authenticate(self, request):
        auth = super().authenticate(request)
        if auth is None:
            return None
            
        user, token = auth
        if not token.is_valid():
            raise AuthenticationFailed('Token is invalid or expired')
            
        return user, token

class CustomOAuth2Validator(OAuth2Validator):
    def validate_bearer_token(self, token, scopes, request):
        if not token:
            return False
            
        request.user = token.user
        request.scopes = scopes
        
        return True