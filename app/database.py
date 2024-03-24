from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, create_engine, Session, ForeignKey, Relationship

engine = create_engine("sqlite:///db.sqlite3", echo=True)

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

def get_session():
    with Session(engine) as session:
        yield session

# def create_tables():
#     SQLModel.metadata.create_all(engine)

# if __name__ == "__main__":
#     create_tables()