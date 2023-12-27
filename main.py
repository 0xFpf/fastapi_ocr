from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Header
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import bw
import ocr
import shutil
from pathlib import Path
import zipfile
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Define path for images folder and create the folder if it doesn't exist
images_dir = Path("images_dir")
images_dir.mkdir(exist_ok=True)
data = None
result=None

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

@app.get("/hello")
async def hello(): 
    return {'message':'welcome human'}

@app.post("/uploadfolder")
async def upload_folder(file: UploadFile = File(...)):
    try:
        # Save the uploaded zip file to the temporary directory
        zip_path = images_dir / file.filename
        with open(zip_path, "wb") as zip_file:
            shutil.copyfileobj(file.file, zip_file)

        # Extract the contents of the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(images_dir)
        
        # Process the extracted files (replace this with your own logic)
        extracted_files = []
        for extracted_folder in images_dir.iterdir():
            if extracted_folder.is_dir():
                for extracted_file in extracted_folder.iterdir():
                    if extracted_file.is_file():
                        extracted_files.append(extracted_file)
        zip_path.unlink()
        print("Extracted files:", extracted_files)

        # Check if file is an image (JPEG or PNG)
        allowed_image_formats = ["jpeg", "jpg", "png"]
        for file in extracted_files:
            if file.suffix[1:].lower() in allowed_image_formats:
                image = bw.convert_img(file)
                image.save(file, format="JPEG")
            else:
                print(f"Invalid file format. file name: {file.name}. File has been removed")
                file.unlink()
        return {"message": f"Folder uploaded, {len(extracted_files)} files extracted."}

    except Exception as e:
        return JSONResponse(content={"message": f"Failed to upload folder. Error: {str(e)}"}, status_code=500)

async def read_image_task(directory: Path):
    global result
    result = await ocr.read_image(directory)

@app.get("/processimages")
async def process_images(background_tasks: BackgroundTasks):
    directory=Path('images_dir')
    if directory.exists():
        background_tasks.add_task(read_image_task, directory)
        return {"message": "Operation started"}
    else:
        raise HTTPException(status_code=404, detail="Folder not found")

@app.get('/index', response_class=HTMLResponse)
async def index(request: Request, hx_request: Optional[str] = Header(None)):
    
    filename=Path('output.json')
    if filename.exists():
        with open(filename, 'r') as file:
            textitems = json.load(file)

    context={'request':request, 'textitems':textitems}
    if hx_request:
        return templates.TemplateResponse("table.html", context)
    return templates.TemplateResponse("index.html", context)

@app.get("/download-csv")
async def download_csv(request: Request):
    file_path = Path("saved_data.csv")  # Replace with the actual path to your saved CSV file
    return FileResponse(file_path, media_type="text/csv", filename="saved_data.csv")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)