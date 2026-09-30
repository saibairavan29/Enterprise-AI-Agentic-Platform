from rest_framework_simplejwt.authentication import JWTAuthentication

class QueryStringOrHeaderJWTAuthentication(JWTAuthentication):
    """
    Extends SimpleJWT's JWTAuthentication to accept JWT tokens via:
    1. Standard Authorization: Bearer <token> header
    2. Query parameter ?token=<token> or ?bearer=<token> (for browser <img>, <iframe>, and file downloads)
    """
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                try:
                    validated_token = self.get_validated_token(raw_token)
                    return self.get_user(validated_token), validated_token
                except Exception:
                    pass

        # Fallback to query param for file/evidence viewing endpoints
        token_param = request.query_params.get('token') or request.query_params.get('bearer')
        if token_param:
            try:
                validated_token = self.get_validated_token(token_param.encode('utf-8'))
                return self.get_user(validated_token), validated_token
            except Exception:
                pass

        return None
