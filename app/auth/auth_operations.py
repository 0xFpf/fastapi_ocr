from fastapi import HTTPException, Depends, status
from typing import Optional, Union
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from app.schemas import Token, TokenData, User, UserInDB, UserCreate, UserOut
from app.database import userModel, get_session
from app.utils import verify_password
from app.auth.auth_handler import decodeJWT
from app.auth.auth_bearer import OAuth2PasswordBearerWithCookie
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

oauth_2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="login")

def get_user_from_db(username:str, session: Session = Depends(get_session)) -> Optional[userModel]:
    statement= select(userModel).where(userModel.username == username)
    try:
        orm_user= session.exec(statement).one()
        return orm_user
    except NoResultFound:
        return None
    except MultipleResultsFound:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Two or more usernames exist')
    
def email_exists(email: str, session) -> bool:
    statement = select(userModel).where(userModel.email == email)
    result = session.exec(statement).fetchall()
    return bool(result)

def authenticate_user(username:str, password:str, session: Session = Depends(get_session)) -> Union[str, bool]:
    user = get_user_from_db(username, session=session)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def get_current_user(token:str=Depends(oauth_2_scheme), session: Session = Depends(get_session)) -> Optional[userModel]:
    credential_exception=HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, detail="Could not validate credentials", headers={'Location': '/login'})
    if token is None:
        logger.info('Token is none, skip decoding.')
        raise credential_exception
    
    try:
        payload= decodeJWT(token)
    except Exception as e:
        logger.debug('Unexpected exception when decoding JWT in get_current_user: ',e)
        raise credential_exception
    
    if payload is None:
        logger.info('Payload is None exception caught')
        raise credential_exception
    
    username: str=payload.get("sub")
    token_data = TokenData(username=username)
    user = get_user_from_db(username=token_data.username, session=session)

    if user is None:
        logger.info('No "sub" found in token, therefore no user found.')
        raise credential_exception
    return user

def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    try:
        if current_user.disabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        return current_user
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing credentials")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))