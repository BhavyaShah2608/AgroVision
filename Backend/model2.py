import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image
import requests
from io import BytesIO
from transformers import AutoImageProcessor, AutoModelForImageClassification

# diseases
disease = {
    "0": "Apple Apple scab",
    "1": "Apple Black rot",
    "2": "Apple Cedar apple rust",
    "3": "Apple healthy",
    "4": "Blueberry healthy",
    "5": "Cherry (including sour) Powdery mildew",
    "6": "Cherry (including sour) healthy",
    "7": "Corn (maize) Cercospora leaf spot Gray leaf spot",
    "8": "Corn (maize) Common rust ",
    "9": "Corn (maize) Northern Leaf Blight",
    "10": "Corn (maize) healthy",
    "11": "Grape Black rot",
    "12": "Grape Esca (Black Measles)",
    "13": "Grape Leaf blight (Isariopsis Leaf Spot)",
    "14": "Grape healthy",
    "15": "Orange Haunglongbing (Citrus greening)",
    "16": "Peach Bacterial spot",
    "17": "Peach healthy",
    "18": "Pepper, bell Bacterial spot",
    "19": "Pepper, bell healthy",
    "20": "Potato Early blight",
    "21": "Potato Late blight",
    "22": "Potato healthy",
    "23": "Raspberry healthy",
    "24": "Soybean healthy",
    "25": "Squash Powdery mildew",
    "26": "Strawberry Leaf scorch",
    "27": "Strawberry healthy",
    "28": "Tomato Bacterial spot",
    "29": "Tomato Early blight",
    "30": "Tomato Late blight",
    "31": "Tomato Leaf Mold",
    "32": "Tomato Septoria leaf spot",
    "33": "Tomato Spider mites Two-spotted spider mite",
    "34": "Tomato Target Spot",
    "35": "Tomato Tomato Yellow Leaf Curl Virus",
    "36": "Tomato Tomato mosaic virus",
    "37": "Tomato healthy"
}

# Load model and processor
processor = AutoImageProcessor.from_pretrained("Diginsa/Plant-Disease-Detection-Project")
model = AutoModelForImageClassification.from_pretrained("Diginsa/Plant-Disease-Detection-Project")

# Example image URL
# image_url = r"C:\Users\USER\Downloads\Potato-leaf-blight.webp"
image_path = '/content/plantvillage dataset/color/Apple___Black_rot/0090d05d-d797-4c99-abd4-3b9cb323a5fd___JR_FrgE.S 8727.JPG"
# Load image from URL
response = requests.get(image_path)
image = Image.open(BytesIO(response.content))

# Preprocess image
inputs = processor(images=image, return_tensors="pt")

# Make prediction
outputs = model(**inputs)
print(outputs)
predicted_class_idx = outputs.logits.argmax().item()

# Print predicted class index
print("Predicted class index:", predicted_class_idx)

# Print predicted class name
print("Predicted class name:", disease[str(predicted_class_idx)])

# Get the first image from the Apple disease folder
base_dir = 'plantvillage dataset/color'
class_dir = os.path.join(base_dir, 'Apple___Black_rot')
image_file = os.listdir(class_dir)[0]
image_path = os.path.join(class_dir, image_file)

# read the image
img = mpimg.imread(image_path)
print(img.shape)
# display the image
plt.imshow(img)
plt.show()
