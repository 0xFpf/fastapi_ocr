from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Header
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import edit
import ocr
import shutil
from pathlib import Path
import zipfile
import csv
from io import StringIO

from sqlmodel import Session, select
from database import imageModel, engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

def get_session():
    with Session(engine) as session:
        yield session

@app.get("/hello")
async def hello(): 
    return {'message':'welcome human'}

@app.post("/uploadfolder")
async def upload_folder(file: UploadFile = File(...), session: Session = Depends(get_session)):
    try:
        # Resets subdirectory
        if images_dir.exists():
            for item in images_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                elif item.is_file():
                    item.unlink()

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
        print("Extracted files:", extracted_files)

        # Filter out non-image files
        # In future I may only take in jpeg or convert any png to jpeg before saving the image
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

        # Add dictionary to db
        statement= select(imageModel)
        result = session.exec(statement).first()
        if result is None:
            for imgmodel in byteimage_list:
                session.add(imageModel(**imgmodel))
            session.commit()

            for item in images_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                elif item.is_file():
                    item.unlink()
        # Need to add an elif for when first row=1st image path, in which case we skip
        # Need to add an else for when there is already data but we just want a new database, so this will clear the db
        else:
            return {"message": "Database full, skipping operation."}
        

        return {"message": f"Folder uploaded, {len(extracted_files)} files extracted."}
    
    except Exception as e:
        return JSONResponse(content={"message": f"Failed to upload folder. Error: {str(e)}"}, status_code=500)

# ocr.py will need to be integrated into this same script to avoid CORS issues while doing streaming response
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