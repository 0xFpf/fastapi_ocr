import easyocr
from pathlib import Path
import json
import csv
import edit

from sqlmodel import Session, select
from database import imageModel, engine

current_path = Path.cwd()
ocr_model= easyocr.Reader(['en'], gpu=True, model_storage_directory=current_path / 'easyocr' ,download_enabled=False)
extracted_files=[]

async def read_image(image_binary_dataset : list):

    length_of_dataset=len(image_binary_dataset)
    progress=0
    picdata=[]
    for binary_image in image_binary_dataset:
        image=edit.convert_to_image(binary_image)
        yield f'data: {{"message": "progress is @ {int(progress)}%"}}\n\n'
        try:
            result = ocr_model.readtext(image)

        # Skips empty images
        except AttributeError:
            progress += (100/length_of_dataset)
            empty_result = ("N/A")
            picdata.append(empty_result)
            continue
        
        progress += (100/length_of_dataset)
        
        # Concatenates scanned sentences together.
        content=""
        for sentence in result:
            content= str(content)+' '+str(sentence[1])
        picdata.append(content)

    # yield f'data: {{"message": "Adding results to database"}}\n\n'

    with Session(engine) as session:
        statement= select(imageModel)
        results = session.exec(statement).all()
        if results:
            for id, content in enumerate(picdata, start=1):
                existing_record = session.get(imageModel, id)
                existing_record.text = content
            session.commit()
        else:
            yield f'data: {{"message": "Error adding to database. Results empty."}}\n\n'
    
    # with Session(engine) as session:
    #     statement = select(imageModel.name, imageModel.text)
    #     results = session.exec(statement).all()
    #     data_list=[]
    #     for item in results:
    #         data = {'name': item[0], 'text': item[1]}
    #         data_list.append(data)
    # json_file_path = 'output.json'
    # with open(json_file_path, 'w', encoding='utf-8') as json_file:
    #     json.dump(data_list, json_file, ensure_ascii=False, indent=2)

    # csv_file_path = "saved_data.csv"
    # with open(csv_file_path, "w", newline="", encoding='utf-8') as csv_file:
    #     csv_writer = csv.DictWriter(csv_file, fieldnames=['name', 'text'])
    #     csv_writer.writeheader()
    #     csv_writer.writerows(data_list)

    yield f'data: {{"message": "Processing complete"}}\n\n'
    yield f'data: {{"event": "close"}}\n\n'