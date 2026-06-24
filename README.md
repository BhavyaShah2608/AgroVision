# AgroVision - Plant Disease Detection & Organic Waste Management 🌿🔍

AgroVision is an environmental sustainability and urban gardening solution designed for smart cities. It combines convolutional machine learning models to detect plant diseases with an organic waste management system that connects communities to organic compost resources.

---

## 🎯 Key Features

- **Plant Disease Detection**: Predicts plant diseases from leaf images with an accuracy of **99%** using a TensorFlow convolutional neural network model.
- **Organic Waste Exchange (Offline Store)**: A system where users can exchange wet organic waste for nutrient-rich organic manure/compost.
- **AI Chatbot Support**: A conversational assistant integrated with Google Gemini API to answer gardening questions, disease symptoms, and organic care tips.
- **Cross-Platform Mobile App**: A Flutter wrapper designed to provide easy mobile access to the web interface.

---

## 🛠️ Project Structure

The project is structured into three main components:
- **`Backend/`**: Flask API server that loads the TensorFlow `.h5` model to process image uploads and serve disease info.
- **`Frontend/`**: A fully responsive static web interface with interactive image uploading, diagnosis history, and AI Chatbot pages.
- **`app/`**: A Flutter mobile app wrapping the web dashboard.

---

## 🚀 Getting Started & Running the Project

Follow these steps to run the backend and frontend locally on Windows.

### 1. Starting the Flask Backend

The backend includes a pre-configured Python virtual environment (`venv`) with TensorFlow, Flask, and all necessary dependencies.

1. Open your terminal (PowerShell, Command Prompt, or Git Bash) and navigate to the project directory.
2. Run the following commands:

**Using PowerShell:**
```powershell
cd Backend
.\venv\Scripts\Activate.ps1
python server.py
```

**Using Command Prompt (cmd):**
```cmd
cd Backend
.\venv\Scripts\activate.bat
python server.py
```

**Using Git Bash:**
```bash
cd Backend
source venv/Scripts/activate
python server.py
```

> [!NOTE]
> The backend server loads a large TensorFlow model (~573MB), which takes around 10–15 seconds to load. You will see `* Running on http://127.0.0.1:5001` once it is ready.

---

### 2. Starting the Frontend Web Server

Because the frontend connects to local APIs and Firebase services, it is best to run it through a local web server to avoid CORS issues.

1. Open a **new terminal tab or window**.
2. Navigate to the project root directory.
3. Start a Python HTTP server on port 8000:
   ```powershell
   python -m http.server 8000
   ```
4. Open your web browser and go to:
   **[http://localhost:8000/Frontend/index.html](http://localhost:8000/Frontend/index.html)**

---

## 🌐 Production Deployment

To deploy the fully functioning web application online for free:

### 1. Frontend (Netlify / Vercel)
- Deploy your GitHub repository to a hosting platform like **Netlify** or **Vercel**.
- Set the **Base directory** to `Frontend` (capital `F`).
- Leave the **Build command** blank.
- Set the **Publish directory** to `.` (or leave it blank).

### 2. Backend API (Hugging Face Spaces)
The backend model weights file (`plant_disease_prediction_model.h5` ~573MB) is too large for GitHub's 100MB file limit. Use **Hugging Face Spaces** (which offers a free 16GB RAM tier) to host it:
1. Create a free account on [Hugging Face](https://huggingface.co/).
2. Create a **New Space**, choose **Docker** as the SDK, and select the **Blank** template.
3. Upload the files inside your local `Backend/` folder directly to the Space repository:
   * `server.py`
   * `diseases.json`
   * `requirements.txt`
   * `Dockerfile` (automatically configures the server for port 7860)
   * `plant_disease_prediction_model.h5` (your model weights, uploaded directly to Hugging Face)
4. Update the backend URL in `Frontend/js/dropdownImage.js` and `Frontend/js/predictions.js` to point to your live Hugging Face Space URL, then push the change to GitHub to trigger Netlify to redeploy.

---

## 📊 Dataset Reference
This project was trained using the [PlantVillage dataset](https://www.kaggle.com/datasets/emmarex/plantdisease), consisting of thousands of healthy and diseased crop leaves across 38 distinct classes.

---

## 👤 Creator
- **Bhavya Shah** 🚀 (Sole Creator & Developer)

---

## 🌿 Conclusion
AgroVision aims to contribute to a greener, healthier, and more sustainable urban environment by facilitating direct community action in recycling organic waste and preserving urban plant life.