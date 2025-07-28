# MediaTool Authentication (basic prototype)
import secrets
from pathlib import Path

class ServiceAuth:
    def __init__(self):
        self.token = self.load_or_create_token()
    
    def load_or_create_token(self):
        token_file = Path.home() / ".mediatool" / "token"
        if token_file.exists():
            return token_file.read_text().strip()
        else:
            token = secrets.token_urlsafe(32)
            token_file.parent.mkdir(exist_ok=True)
            token_file.write_text(token)
            return token

    def verify_token(self, auth_header):
        """Check if the Authorization header contains the correct token."""
        return auth_header == f"Bearer {self.token}"

    def verify_request(self, request):
        auth_header = request.headers.get('Authorization')
        return self.verify_token(auth_header)

# Example Flask usage:
# from flask import request, abort
# auth = ServiceAuth()
# def verify_auth():
#     auth_header = request.headers.get('Authorization')
#     if not auth.verify_token(auth_header):
#         abort(401)
