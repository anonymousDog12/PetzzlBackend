import os
from google.cloud import vision_v1
import io
from dotenv import load_dotenv


def is_pet_or_animal_image(image_path, confidence_threshold=0.5):
    """Checks if the image is of a pet/animal."""
    client = vision_v1.ImageAnnotatorClient()

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision_v1.Image(content=content)
    response = client.label_detection(image=image)
    labels = response.label_annotations

    pet_related_terms = ['pet', 'dog', 'cat', 'animal',
                         'bird', 'fish', 'hamster', 'rabbit', 'reptile']
    for label in labels:
        if label.description.lower() in pet_related_terms and label.score >= confidence_threshold:
            print(
                f"Detected: {label.description} with {label.score * 100:.2f}% confidence")
            return True

    return False


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
    test_image_path = '/Users/erin/Downloads/IMG_7190.HEIC'
    result = is_pet_or_animal_image(test_image_path)
    print("Is this a pet/animal image?", result)
