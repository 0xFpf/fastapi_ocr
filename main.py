from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Header, status, Cookie
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
from database import imageModel, engine
from fastapi.middleware.cors import CORSMiddleware

SECRET_KEY="xxx"
ALGORITHM="xxx"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class Token(BaseModel):
    access_token: str
    token_type: str

# data encoded by our token
class TokenData(BaseModel):
    username: str or None = None

class User(BaseModel):
    username: str
    email: str or None = None
    full_name: str or None = None
    disabled: bool or None = None

class UserInDB(User):
    hashed_password: str

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

def get_user(tmp_db, username:str):
    if username in tmp_db:
        user_data = tmp_db[username]
        return UserInDB(**user_data)
    
def authenticate_user(tmp_db, username:str, password:str):
    user = get_user(tmp_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user
    
def create_access_token(data: dict, expires_delta: timedelta or None=None):
    to_encode=data.copy()
    if expires_delta:
        expire=datetime.utcnow()+expires_delta
    else:
        expire=datetime.utcnow()+timedelta(minutes=2)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request):
    credential_exception=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        token = request.cookies.get("access_token")
        if token is None:
            raise credential_exception
        if token.startswith("Bearer "):
            token = token.split("Bearer ")[1]
        payload= jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str=payload.get("sub")
        if username is None:
            raise credential_exception
        token_data = TokenData(username=username)
    except JWTError:
        print("JWT error")
        return credential_exception

    user = get_user(tmp_db, username=token_data.username)
    if user is None:
        print("get_user is none")
        raise credential_exception
    return user

# this filters out disabled=True users
async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data:OAuth2PasswordRequestForm = Depends()):
    user=authenticate_user(tmp_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password", headers={"WWW-Authenticate":"Bearer"})
    access_token_expires=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token= create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    # Set the access token as an HTTP cookie with HttpOnly flag
    response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 30,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 30,
        path="/",
    )
    return response


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/users/me/items")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return current_user

# App gave me a CORS error when using ocr.py along with StreamingResponse, for now I'm using the below settings
# Not sure what to set the origin as once it is in prod, for now allowing all origins.
# Refactoring ocr.py into main would allow me to get rid of this.
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

def get_session():
    with Session(engine) as session:
        yield session

@app.get("/hello")
async def hello(): 
    return {'message':'welcome human'}

# @app.get("/login")
# async def login(email: str = Form(...)):
#     if email exists in database:
#         find username then authenticate
#     else:
#         return {"message": "Check your email to finish logging in."}

@app.post("/uploadfolder")
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

        # Filter out non-image files
        # # In future I may only take in jpeg or convert any png to jpeg before saving the image
        # # I could also implement multiple file uploads and use DropzoneJs for a better UX
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