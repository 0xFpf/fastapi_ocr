from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, create_engine, Session, ForeignKey, Relationship
from decouple import config
# DB_URL=f'sqlite://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}'
DB_URL= config("DB_URL")
engine = create_engine(f"sqlite:///{DB_URL}", echo=True)

class userModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    hashed_password: str
    full_name: str
    disabled: bool = False
    created_at: datetime = Field(default=datetime.now(timezone.utc))
    # images: List["imageModel"] = Relationship("imageModel", back_populates="user")
    
class imageModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_object: bytes
    name: str
    text: str = ""
    owner_id: Optional[int] = Field(default=None, foreign_key="usermodel.id")
    # user: userModel = Relationship("UserModel", back_populates="images")

def create_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

if __name__ == "__main__":
    create_tables()