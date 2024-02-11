from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Header, status, Cookie, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import edit
import ocr
import shutil
from pathlib import Path
import zipfile
import csv
from io import StringIO

from sqlmodel import Session, select, delete
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from database import imageModel, userModel, engine
from fastapi.middleware.cors import CORSMiddleware

from app.auth.auth_handler import decodeJWT, signJWT
from app.auth.auth_bearer import jwt_bearer
from app.schemas import Token, TokenData, User, UserInDB, UserCreate
from decouple import config
JWT_EXPIRES = int(config("ACCESS_TOKEN_EXPIRE_MINUTES"))

oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def verify_password(plain_password, hashed_password):
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password=hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc , hashed_password)

def get_password_hash(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    hashed_password = hashed_password.decode('utf-8')
    return hashed_password

def get_session():
    with Session(engine) as session:
        yield session

def get_user(username:str, session: Session = Depends(get_session)):
    statement= select(userModel).where(userModel.username == username)
    try:
        user = session.exec(statement).one()
        print(user)
        return user
    except NoResultFound:
        return None
    except MultipleResultsFound:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Two or more usernames exist')

def authenticate_user(username:str, password:str, session: Session = Depends(get_session)):
    user = get_user(username, session=session)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict):
    payload=data.copy()
    expires_delta=timedelta(minutes=JWT_EXPIRES)
    expire=datetime.utcnow()+expires_delta
    payload.update({"exp": expire})
    encoded_jwt = signJWT(payload)
    return encoded_jwt

async def get_current_user(token:str=Depends(jwt_bearer), session: Session = Depends(get_session)):
    credential_exception=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload= decodeJWT(token)
        username: str=payload.get("sub")
        if username is None:
            raise credential_exception
        token_data = TokenData(username=username)
    except:
        return credential_exception

    user = get_user(username=token_data.username, session=session)
    if user is None:
        raise credential_exception
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data:OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user=authenticate_user(form_data.username, form_data.password, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate":"Bearer"})
    
    access_token= create_access_token(data={"sub": user.username})

    # Set the access token as an HTTP cookie with HttpOnly flag
    response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=JWT_EXPIRES * 2,
        path="/",
    )
    return response

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# App gave me a CORS error when using ocr.py along with StreamingResponse. Would need to refactor ocr.py into main.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define path for images folder and create if it doesn't exist
images_dir = Path("images_dir")
images_dir.mkdir(exist_ok=True)
data=None

def reset_dir():
    if images_dir.exists():
        for item in images_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file():
                item.unlink()

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

@app.get("/hello")
async def hello(): 
    return {'message':'welcome human'}

def email_exists(email: str, session) -> bool:
    statement = select(userModel).where(userModel.email == email)
    result = session.exec(statement).fetchall()
    return bool(result)

@app.post("/signup", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, session: Session = Depends(get_session)):
        # If db empty then add dictionary to db
        hashed_password=get_password_hash(user.password)
        user_dict = user.model_dump()
        user_dict.pop("password")
        user_dict["hashed_password"] = hashed_password
        print(f"user data:{user_dict}")


        if email_exists(user.email, session):
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            new_user = userModel(**user_dict)
            session.add(new_user)
            session.commit()
            return {"message": "New user added to database."}

@app.post("/uploadfolder", status_code=status.HTTP_201_CREATED)
async def upload_folder(file: UploadFile = File(...), session: Session = Depends(get_session)):
    try:
        # Resets subdirectory
        reset_dir()
        # Temporarily save the uploaded zip file to images_dir(ectory)
        zip_path = images_dir / file.filename
        with open(zip_path, "wb") as zip_file:
            shutil.copyfileobj(file.file, zip_file)

        # Extract zip contents
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(images_dir)
        
        # Generate list of paths
        extracted_files = []
        for extracted_folder in images_dir.iterdir():
            if extracted_folder.is_dir():
                for extracted_file in extracted_folder.iterdir():
                    if extracted_file.is_file():
                        extracted_files.append(extracted_file)
        zip_path.unlink()

        # # In future I may only take in jpeg or convert any png to jpeg before saving the image, could also implement multiple file uploads
        allowed_image_formats = ["jpeg", "jpg", "png"]
        
        image_list=[]
        for file in extracted_files:
            if file.suffix[1:].lower() in allowed_image_formats:
                # Converts image to bw and into bytes
                image = edit.convert_img(file)
                image = edit.convert_to_bytes(image)
                image_list.append([image, str(file)])
            else:
                print(f"Invalid file format. file name: {file.name}. File has been removed")
                file.unlink()
        # Generate dictionary to add to db
        byteimage_list=[]
        for id, item in enumerate(image_list, start=1):
            byteimage_item = {'id': id, 'image_object': item[0], 'name': item[1]}
            byteimage_list.append(byteimage_item)

        # If db empty then add dictionary to db
        statement= select(imageModel)
        result = session.exec(statement).first()
        if result is None:
            for imgmodel in byteimage_list:
                session.add(imageModel(**imgmodel))
            session.commit()
            reset_dir()

        # If db is equal to images extracted then ignore and skip
        elif result.name==byteimage_list[0]['name']:
            print('result==byteimage_list')
            reset_dir()
            return {"message": "Database full, skipping operation."}
        
        # If db exists but images are new then clear the db and add new images
        else:
            delete_statement = delete(imageModel)
            session.exec(delete_statement)
            session.commit()
            # deleted_rows = session.exec(delete_statement).rowcount
            # session.commit()
            # print(f"Deleted {deleted_rows} rows from the imageModel table.")
            for imgmodel in byteimage_list:
                session.add(imageModel(**imgmodel))
            session.commit()
            reset_dir()
        

        return {"message": f"Folder uploaded, {len(extracted_files)} files extracted."}
    
    except Exception as e:
        return JSONResponse(content={"message": f"Failed to upload folder. Error: {str(e)}"}, status_code=500)

# ocr.py will need to be integrated into here to avoid CORS issues while streaming response
@app.get("/sse/processimages")
async def processimages(session: Session = Depends(get_session)):
    statement= select(imageModel.image_object)
    results = session.exec(statement).all()
    if results:
        return StreamingResponse(ocr.read_image(results), media_type="text/event-stream")
    else:
        return {"message": "Err 404, Images not found."}

@app.get('/loadtable', response_class=HTMLResponse)
async def loadtable(request: Request, hx_request: Optional[str] = Header(None), session: Session = Depends(get_session)):
    statement = select(imageModel.name, imageModel.text)
    results = session.exec(statement).all()
    textitems=[]
    for item in results:
        data = {'name': item[0], 'text': item[1]}
        textitems.append(data)
    # creates context dict, loads request and json data, passes 'context' to table.html
    context={'request':request, 'textitems':textitems}
    if hx_request:
        return templates.TemplateResponse("table.html", context)
    raise HTTPException(status_code=404, detail="Images text output not found, process some images and try again.")

@app.get("/download-csv")
async def download_csv(request: Request, session: Session = Depends(get_session)):
    statement = select(imageModel.name, imageModel.text)
    results = session.exec(statement).all()
    textitems=[]
    for item in results:
        data = {'name': item[0], 'text': item[1]}
        textitems.append(data)
    csv_file = StringIO()
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['name', 'text'])
    for item in textitems:
        csv_writer.writerow([item['name'], item['text']])
    # Move the file pointer to the beginning of the file
    csv_file.seek(0)
    return StreamingResponse(iter([csv_file.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=saved_data.csv"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)