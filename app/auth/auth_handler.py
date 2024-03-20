from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
from decouple import config

JWT_SECRET = config("SECRET_KEY")
JWT_ALGORITHM = config("ALGORITHM")
JWT_EXPIRES = int(config("ACCESS_TOKEN_EXPIRE_MINUTES"))

def signJWT(payload: dict) -> str:
    try:
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    except Exception as e:
        print("Error signing JWT:", e)
        return None

def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        expiry_time_utc = datetime.fromtimestamp(decoded_token["exp"], tz=timezone.utc)
        current_time = datetime.now(timezone.utc)
        if expiry_time_utc >= current_time:
            return decoded_token 
        else:
            print("Expired JWT")
            return None
    except JWTError as e:
        print("Error decoding JWT:", e)
        return None

def create_access_token(data: dict) -> str:
    payload=data.copy()
    expires_delta=timedelta(minutes=JWT_EXPIRES*0.05)
    expire=datetime.now(timezone.utc)+expires_delta
    payload.update({"exp": expire})
    encoded_jwt = signJWT(payload)
    return encoded_jwt