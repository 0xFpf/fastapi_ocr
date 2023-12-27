import easyocr
from pathlib import Path
import json
import csv

current_path = Path.cwd()
ocr_model= easyocr.Reader(['en'], gpu=True, model_storage_directory=current_path / 'easyocr' ,download_enabled=False)
extracted_files=[]

async def read_image(directory : Path):
    for extracted_folder in directory.iterdir():
        if extracted_folder.is_dir():
            for extracted_file in extracted_folder.iterdir():
                if extracted_file.is_file():
                    extracted_files.append(extracted_file)

    length_of_extracted_files=len(extracted_files)
    progress=0
    picdata=[]
    for file_path in extracted_files:
        print(f"progress is @ {progress}%")
        try:
            result = ocr_model.readtext(str(file_path))

        # Skips empty images
        except AttributeError:
            progress += (100/length_of_extracted_files)
            continue
        
        progress += (100/length_of_extracted_files)
        progress_amount=str(progress)
        
        # Concatenates scanned sentences together.
        content=""
        for sentence in result:
            content= str(content)+' '+str(sentence[1])

        # Adds each image content to a list/database
        contentArray = (str(file_path), content)
        picdata.append(contentArray)
    
    transformed_data = []

    for item in picdata:
        transformed_item = {'name': item[0], 'text': item[1]}
        transformed_data.append(transformed_item)
    print(transformed_data)

    json_file_path = 'output.json'
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(transformed_data, json_file, ensure_ascii=False, indent=2)

    csv_file_path = "saved_data.csv"
    with open(csv_file_path, "w", newline="", encoding='utf-8') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=['name', 'text'])
        csv_writer.writeheader()
        csv_writer.writerows(transformed_data)

    return 'done'