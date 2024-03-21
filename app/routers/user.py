from fastapi import HTTPException, Depends, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from typing import Optional, Union
from sqlmodel import Session, select, delete
from app.schemas import Token, TokenData, User, UserInDB, UserCreate, UserOut
from app.database import userModel, get_session
from app.utils import get_password_hash
from app.auth.auth_handler import create_access_token
from app.auth.auth_operations import email_exists, authenticate_user, get_current_active_user

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_for_access_token(form_data:OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)) -> Token:
    user=authenticate_user(form_data.username, form_data.password, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect username or password", headers={"WWW-Authenticate":"Bearer"})
    
    access_token= create_access_token(data={"sub": user.username})

    # Set the access token as an HTTP cookie with HttpOnly flag
    response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=60 * 10, # 10 min
        path="/",
    )
    return response

@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register_user(user: UserCreate, session: Session = Depends(get_session)):
        # If db empty then add dictionary to db
        hashed_password=get_password_hash(user.password)
        user_dict = user.model_dump()
        user_dict.pop("password")
        user_dict["hashed_password"] = hashed_password
        print(f"user data:{user_dict}")


        if email_exists(user.email, session):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        else:
            new_user = userModel(**user_dict)
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user