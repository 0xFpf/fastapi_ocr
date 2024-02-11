#The goal of this file is to check whether the request is authorized or not [ verification of the proteced route]
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth_handler import decodeJWT


def verify_jwt(jwtoken: str) -> bool:
    try:
        payload = decodeJWT(jwtoken)
        return True if payload else False
    except:
        return False

async def jwt_bearer(request: Request, auto_error: bool = True):
    # credentials: HTTPAuthorizationCredentials = await HTTPBearer(auto_error=auto_error)(request)
    token = request.cookies.get("access_token", None)
    
    if token:
        if token.startswith("Bearer "):
            token = token.split("Bearer ")[1]
            if verify_jwt(token):
                return token
            else:
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
        else:
                raise HTTPException(status_code=403, detail="Invalid authorization token.")
    else:
        raise HTTPException(status_code=403, detail="Invalid authorization code.")
    
    # print(credentials)
    # if credentials:
    #     if not credentials.scheme == "Bearer":
    #         raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
    #     if not verify_jwt(credentials.credentials):
    #         raise HTTPException(status_code=403, detail="Invalid token or expired token.")
    #     return credentials.credentials
    # else:
    #     raise HTTPException(status_code=403, detail="Invalid authorization code.")