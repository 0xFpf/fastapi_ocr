from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Header, status, Cookie, Form, Query
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Union
import shutil
from pathlib import Path
import zipfile
import csv
from io import StringIO

from sqlmodel import Session, select, delete
from app.database import imageModel, userModel, get_session

import app.edit_image as edit_image, app.ocr as ocr
from app.auth.auth_bearer import OAuth2PasswordBearerWithCookie
from app.schemas import Token, TokenData, User, UserInDB, UserCreate, UserOut
from app.auth.auth_operations import get_current_active_user
from app.routers import user


oauth_2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="login")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.include_router(user.router)



# #not sure if this needs deprecation: Define path for images folder and create if it doesn't exist + reset directory
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

@app.get("/hello", status_code=status.HTTP_200_OK)
async def hello(): 
    return {'message':'welcome human'}

@app.post("/uploadfolder", status_code=status.HTTP_201_CREATED)
async def upload_folder(file: UploadFile = File(...), current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    try:
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
                image = edit_image.convert_img(file)
                image = edit_image.convert_to_bytes(image)
                image_list.append([image, str(file)])
            else:
                print(f"Invalid file format. file name: {file.name}. File has been removed")
                file.unlink()

        owner_id=current_user.id
      
        # Generate dictionary to add to db
        byteimage_list=[]
        for id, item in enumerate(image_list, start=1):
            byteimage_item = {'id': id, 'image_object': item[0], 'name': item[1], 'owner_id': owner_id}
            byteimage_list.append(byteimage_item)

        statement= select(imageModel).where(imageModel.owner_id == owner_id)
        existing_entries = session.exec(statement).first()

        # If db empty then add dictionary to db
        if existing_entries is None:
            for imgmodel in byteimage_list:
                session.add(imageModel(**imgmodel))
            session.commit()
            reset_dir()

        # If db is equal to images extracted then ignore and skip
        elif existing_entries.name==byteimage_list[0]['name']:
            print('result==byteimage_list')
            reset_dir()
            return {"message": "Database full, skipping operation."}
        
        # If db exists but images are new then clear the db and add new images
        else:
            delete_statement = delete(imageModel).where(imageModel.owner_id == owner_id)
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
async def processimages(current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    owner_id=current_user.id
    statement= select(imageModel.image_object).where(imageModel.owner_id == owner_id)
    results = session.exec(statement).all()
    if results:
        return StreamingResponse(ocr.read_image(results), media_type="text/event-stream")
    else:
        return {"message": "Err 404, Images not found."}

@app.get('/loadtable', response_class=HTMLResponse)
async def loadtable(request: Request, hx_request: Optional[str] = Header(None), session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    owner_id=current_user.id
    statement= select(imageModel.name, imageModel.text).where(imageModel.owner_id == owner_id)
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


@app.get('/search', response_class=HTMLResponse)
async def loadtable(request: Request, hx_request: Optional[str] = Header(None), session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user), query: Optional[str] = Query(None)):
    owner_id=current_user.id
    statement= select(imageModel.name, imageModel.text).where((imageModel.owner_id == owner_id) & (imageModel.text.like(f'%{query}%')))
    results = session.exec(statement).all()
    textitems=[]
    for item in results:
        data = {'name': item[0], 'text': item[1]}
        textitems.append(data)
    context={'request':request, 'textitems':textitems}
    if hx_request:
        return templates.TemplateResponse("table.html", context)
    raise HTTPException(status_code=404, detail="Images text output not found, process some images and try again.")

@app.get("/download-csv")
async def download_csv(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    owner_id=current_user.id
    statement= select(imageModel.name, imageModel.text).where(imageModel.owner_id == owner_id)
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