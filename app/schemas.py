from pydantic import BaseModel, EmailStr, NaiveDatetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str or None = None
    # id: Optional[str] = None

class User(BaseModel):
    username: str
    email: str or None = None
    full_name: str or None = None
    disabled: bool or None = None

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str

    class Config:
        orm_model = True

# not implemented atm, might delete
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# class UserAll(BaseModel):
#     id:int
#     email: EmailStr
#     full_name:str
#     created_at: NaiveDatetime
#     hashed_password: str
#     username: str
#     disabled: bool

#     class Config:
#         orm_model = True