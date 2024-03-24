from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timezone, timedelta
from decouple import config
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JWT_SECRET = config("SECRET_KEY")
JWT_ALGORITHM = config("ALGORITHM")
JWT_EXPIRES = int(config("ACCESS_TOKEN_EXPIRE_MINUTES"))

def signJWT(payload: dict) -> str:
    try:
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    except Exception as e:
        logger.info("Error signing JWT:", e)
        return None

def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        expiry_time_utc = datetime.fromtimestamp(decoded_token["exp"], tz=timezone.utc)
        current_time = datetime.now(timezone.utc)
        logger.info(f'expiry_time vs curr time: {expiry_time_utc} > {current_time}')
        if expiry_time_utc >= current_time:
            return decoded_token 
        else:
            logger.info("Exception when decoding JWT: JWT expiry time has elapsed.")
            return None
    except ExpiredSignatureError as e:
        logger.info("Exception when decoding JWT: Signature has expired.")
        return None
    except JWTError as e:
        logger.debug("Unexpected exception when decoding JWT: ", e)
        return None

def create_access_token(data: dict) -> str:
    payload=data.copy()
    expires_delta=timedelta(seconds=JWT_EXPIRES)
    expire=datetime.now(timezone.utc)+expires_delta
    payload.update({"exp": expire})
    encoded_jwt = signJWT(payload)
    return encoded_jwt