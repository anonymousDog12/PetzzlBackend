import os
from google.cloud import vision_v1
import io
from dotenv import load_dotenv


def is_suitable_pet_image(image_path, confidence_threshold=0.5):
    """Checks if the image is suitable for the app: an animal image without inappropriate content."""
    client = vision_v1.ImageAnnotatorClient()

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision_v1.Image(content=content)

    # Checking for pets/animals
    response_labels = client.label_detection(image=image)
    labels = response_labels.label_annotations
    pet_related_terms = ['pet', 'dog', 'cat', 'animal', 'horse', 'turtle',
                         'bird', 'fish', 'hamster', 'rabbit', 'reptile']
    is_animal = False
    for label in labels:
        print(f"Label: {label.description}, Score: {label.score}")
        if label.description.lower() in pet_related_terms and label.score >= confidence_threshold:
            print(
                f"Detected animal: {label.description} with {label.score * 100:.2f}% confidence")
            is_animal = True
            break

    # If an animal is detected, check for explicit content
    if is_animal:
        response_safe_search = client.safe_search_detection(image=image)
        safe = response_safe_search.safe_search_annotation

        # Print the safe search detection results
        print(
            f"Adult content score: {safe.adult}, Violence score: {safe.violence}")

        # Defining thresholds for inappropriate content
        thresholds = {
            'adult': vision_v1.Likelihood.POSSIBLE,
            'violence': vision_v1.Likelihood.POSSIBLE
        }

        if safe.adult < thresholds['adult'] and safe.violence < thresholds['violence']:
            return True
        else:
            print("Image failed the check: Contains inappropriate content.")
            return False
    else:
        print("No animal detected in the image.")
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
    test_image_path = '/Users/erin/Desktop/lp_image2.jpeg'
    result = is_suitable_pet_image(test_image_path)
    print("Is this image suitable for Petzzl app?", result)
