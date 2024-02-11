import time
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Dict
from decouple import config

JWT_SECRET = config("SECRET_KEY")
JWT_ALGORITHM = config("ALGORITHM")
JWT_EXPIRES = config("ACCESS_TOKEN_EXPIRE_MINUTES")

# Function returns generated tokens
def token_response(token:str):
    return{
        "access token":token,
        "token_type": "bearer"
    }

# function used for signing the JWT string
# def signJWT(user_id: str) -> Dict[str, str]:
#     payload = {
#         "sub": user_id,
#         "exp": time.time() + 600
#     }
#     token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

#     return token_response(token)


def signJWT(payload: dict) -> str:
    try:
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    except:
        return None

def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if decoded_token["exp"] >= time.time():
            return decoded_token 
        else:
            return None
    except:
        return None