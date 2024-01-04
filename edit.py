from PIL import Image
from io import BytesIO

# Convert the image to a bytes object and return it as binary data
def convert_bytes(input_image):
    image_io = BytesIO()
    input_image.save(image_io, format="JPEG")
    image_binary_data = image_io.getvalue()
    return image_binary_data

# Convert the image to grayscale
def convert_img(input_image):
    image = Image.open(input_image)
    gray_image = image.convert("L")
    return gray_image

# Convert the image from PNG to JPEG
def convert_png(input_image):
    png_image = Image.open(input_image)
    png_image.convert('RGB')
    return png_image