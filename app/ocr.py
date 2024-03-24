#     # STANDALONE IMPLEMENTATION OF OCR WITH EASYOCR, NOT IN USE
# import easyocr
# from pathlib import Path
# import app.edit_image as edit_image

# from sqlmodel import Session, select
# from app.database import imageModel, engine

# current_path = Path.cwd()
# ocr_model= easyocr.Reader(['en'], gpu=False, model_storage_directory=current_path / 'easyocr' ,download_enabled=False)
# extracted_files=[]

# async def read_image(image_binary_dataset : list):

#     length_of_dataset=len(image_binary_dataset)
#     progress=0
#     picdata=[]
#     for binary_image in image_binary_dataset:
#         image=edit_image.convert_to_image(binary_image)
#         yield f'data: {{"message": "progress is @ {int(progress)}%"}}\n\n'
#         try:
#             result = ocr_model.readtext(image)

#         # Skips some empty images that cause exceptions
#         except AttributeError:
#             progress += (100/length_of_dataset)
#             empty_result = ("N/A")
#             picdata.append(empty_result)
#             continue
        
#         progress += (100/length_of_dataset)
        
#         # Concatenates scanned sentences together.
#         content=""
#         for sentence in result:
#             content= str(content)+' '+str(sentence[1])
#         picdata.append(content)

#     # Adds results to database
#     with Session(engine) as session:
#         statement= select(imageModel)
#         results = session.exec(statement).all()
#         if results:
#             for id, content in enumerate(picdata, start=1):
#                 existing_record = session.get(imageModel, id)
#                 existing_record.text = content
#             session.commit()
#         else:
#             yield f'data: {{"message": "Error adding to database. Results empty."}}\n\n'
    
#     yield f'data: {{"message": "Processing complete"}}\n\n'
#     yield f'data: {{"event": "close"}}\n\n'