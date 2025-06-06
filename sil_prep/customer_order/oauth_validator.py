from oauth2_provider.oauth2_validators import OAuth2Validator

class CustomOAuth2Validator(OAuth2Validator):
    def get_additional_claims(self, request):
        return {
            "given_name": request.user.first_name,
            "family_name": request.user.last_name,
            "email": request.user.email,
            "phone_number": request.user.phone_number,
        }
    
    def validate_user(self, username, password, client, request, *args, **kwargs):
        user = super().validate_user(username, password, client, request, *args, **kwargs)
        if not user:
            return False
            
        request.user = user
        return True