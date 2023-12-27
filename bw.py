from PIL import Image
from io import BytesIO

def convert_bytes(input_image):
    # Open the image file
    image_file = BytesIO(input_image)
    image = Image.open(image_file)

    # Convert the image to grayscale (black and white)
    gray_image = image.convert("L")

    return gray_image

def convert_img(input_image):
    # Open the image file
    image = Image.open(input_image)
    # Convert the image to grayscale (black and white)
    gray_image = image.convert("L")

    return gray_image