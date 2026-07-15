---

# 🗓️ Group Timetable Heatmap Generator

This tool uses OpenCV and Tesseract OCR to extract schedule slots from university timetable screenshots, aggregates individual schedules, and generates a visual availability heatmap to help groups find the perfect common free time.

---

## 🛠️ Prerequisites & Setup

Before running the script, you need to install the external OCR engine and the correct Python libraries.

### 1. Install Tesseract OCR Engine

Because this project relies on **PyTesseract** to read text from images, you must install the actual Tesseract engine on your machine:

* **Windows:** Download and run the installer from [UB Mannheim Tesseract](https://www.google.com/search?q=https://github.com/UB-Mannheim/tesseract/wiki). By default, it installs to `C:\Program Files\Tesseract-OCR\tesseract.exe`.
* **macOS:** Install via Homebrew:
```bash
brew install tesseract

```


* **Linux (Ubuntu/Debian):** Install via apt:
```bash
sudo apt update
sudo apt install tesseract-ocr

```



### 2. Install Python Dependencies

Run the following command in your terminal to install the required libraries.

> 💡 *Note: The core imaging library is packaged as `opencv-python` (not `cv2`), and `re` is built right into Python, so you don't need to install it!*

```bash
pip install opencv-python pytesseract numpy matplotlib

```

---

## ⚙️ Configuration

Open `main.py` in your code editor and check the following two items:

1. **Tesseract Path (Windows Users):**
Ensure line 10 points directly to your Tesseract installation executable:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

```


*(Mac/Linux users can typically comment this line out, as the system binary path is automatically discovered).*
2. **Slot Template Customization:**
The `SLOT_TEMPLATE` matrix is currently configured for a standard university day/night slot system (e.g., `A1`, `F1`, `LUNCH`). If your university uses a different coding scheme, simply edit the string arrays inside `SLOT_TEMPLATE` to match your campus codes.

---

## 🚀 How to Use

### 1. Structure Your Directory

Create a folder named `timetables` in the exact same directory where `main.py` lives. Drop all group member timetable screenshots into it. Use the filename as the person's name (e.g., `Alice.png`, `Bob.jpg`).

Your repository structure should look like this:

```text
your-project-folder/
├── timetables/
│   ├── Alice.png
│   ├── Bob.jpg
│   └── Charlie.jpeg
└── main.py

```

### 2. Run the Script

Execute the main file from your terminal:

```bash
python main.py

```

---

## 📊 Expected Output

Upon a successful run, the script will:

1. Print processing confirmations in your terminal for each file found.
2. Launch a popup window displaying an interactive matplotlib heatmap.
3. Automatically save a high-resolution version of the map as **`group_heatmap.png`** in your project directory.

Green blocks signify highly available slots, while orange/red blocks indicate heavy scheduling conflicts!
