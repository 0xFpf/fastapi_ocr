import os
import app.edit_image as edit_image
from sqlmodel import Session, select
from app.database import imageModel, engine
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './eternal-reserve-418212-53c67094eae4.json'

extracted_files=[]

async def read_image(image_binary_dataset : list):
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()

    length_of_dataset=len(image_binary_dataset)
    progress=0
    picdata=[]
    for binary_image in image_binary_dataset:
        content=edit_image.convert_to_image(binary_image)
        yield f'data: {{"message": "progress is @ {int(progress)}%"}}\n\n'

        image = vision.Image(content=binary_image)

        response = client.text_detection(image=image)
        texts = response.text_annotations

        if response.error.message:
            logger.info('response error: ', response.error.message)
            logger.info("https://cloud.google.com/apis/design/errors".format(response.error.message))
            empty_result = ("N/A")
            picdata.append(empty_result)

        elif not texts:
            logger.info('Empty image error, skipping.')
            empty_result = ("N/A")
            picdata.append(empty_result)

        else:
            texts = response.text_annotations
            picdata.append(texts[0].description)

        progress += (100/length_of_dataset)

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
    
    yield f'data: {{"message": "Processing complete"}}\n\n'
    yield f'data: {{"event": "close"}}\n\n'