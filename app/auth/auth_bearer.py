from fastapi import Request, HTTPException

from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi import Request
from fastapi.security.utils import get_authorization_scheme_param
from fastapi import HTTPException
from fastapi import status
from typing import Optional, Dict
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get("access_token")  #changed to accept access token from httpOnly Cookie
        logger.info(f"access_token is {authorization}")

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                logger.info("self.auto_error, No eligible token found")
                return None
                # raise HTTPException(
                #     status_code=status.HTTP_401_UNAUTHORIZED,
                #     detail="Not authenticated",
                #     headers={"WWW-Authenticate": "Bearer"},
                # )
            else:
                logger.info("No token found")
                return None
        return param
