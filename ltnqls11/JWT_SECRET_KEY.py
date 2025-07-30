import os
import base64

# 32바이트 (256비트)의 무작위 바이트 생성
# JWT HS256 알고리즘에 적합한 길이입니다.
secret_bytes = os.urandom(32)

# Base64로 인코딩하여 문자열 형태로 변환
secret_key = base64.urlsafe_b64encode(secret_bytes).decode('utf-8')

print(f"생성된 JWT_SECRET_KEY: {secret_key}")
print(f"길이: {len(secret_key)} 문자")