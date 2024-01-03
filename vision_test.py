import os
from google.cloud import vision_v1
import io
from dotenv import load_dotenv


def detect_labels(image_path):
    """Detects labels in the file."""
    client = vision_v1.ImageAnnotatorClient()

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision_v1.Image(content=content)
    response = client.label_detection(image=image)
    labels = response.label_annotations

    print('Labels:')
    for label in labels:
        print(label.description)


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Set the GOOGLE_APPLICATION_CREDENTIALS environment variable
    google_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if google_credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials_path
    else:
        print("Google Application Credentials not found.")
        exit()

    # Replace 'path_to_your_image.jpg' with the path to your test image file
    test_image_path = './lp_image.jpeg'
    detect_labels(test_image_path)
