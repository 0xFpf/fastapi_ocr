from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, ForeignKey, Relationship

DB_FILE= 'db.sqlite3'
engine = create_engine(f"sqlite:///{DB_FILE}", echo=True)

class userModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    hashed_password: str
    full_name: str
    disabled: bool = False
    # images: List["imageModel"] = Relationship("imageModel", back_populates="user")
   
    # class Config:
    # tablename = "user"

    # __table_args__ = (
    #     UniqueConstraint("username", "email", name="unique_username_email"),
    # )
    
class imageModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_object: bytes
    name: str
    text: str = ""
    user_id: Optional[int] = Field(default=None, foreign_key="usermodel.id")
    # user: userModel = Relationship("UserModel", back_populates="images")
       
def create_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_tables()