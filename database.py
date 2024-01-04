from typing import Optional
from sqlmodel import Field, SQLModel, create_engine

DB_FILE= 'db.sqlite3'
engine = create_engine(f"sqlite:///{DB_FILE}", echo=True)

class imageModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_object: bytes
    name: str
    text: str = ""
    
def create_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_tables()