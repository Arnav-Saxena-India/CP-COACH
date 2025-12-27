# Competitive Programming Coach

An intelligent Chrome extension that acts as your personal Competitive Programming coach. It analyzes your performance on Codeforces, identifies your weak topics, and recommends problems to help you improve.

## 📥 Installation

**Note:** This extension uses a hosted backend server, so no extra setup is required.

1.  **Download** this repository (Code -> Download ZIP) and extract it.
2.  Open **Google Chrome** and go to `chrome://extensions/`.
3.  Enable **Developer mode** (top right corner toggle).
4.  Click **Load unpacked**.
5.  Select the `extension` folder from this repository.
6.  Pin the extension to your toolbar and start solving.

## 🚀 Usage

1.  **Open the Extension:** Click the CP Coach icon in your Chrome toolbar.
2.  **Enter Your Handle:**
    *   **Auto-Detect:** Open [Codeforces.com](https://codeforces.com) in a new tab, and the extension will automatically detect your logged-in username.
    *   **Manual:** Alternatively, just type your Codeforces username into the input box.
3.  **Get Better:** View your weakness analysis and start solving recommended problems!

## ⚡ Key Features

*   **Weakness Analysis:** Automatically detects topics you struggle with based on your submission history.
*   **Smart Recommendations:** Suggests problems tailored to your rating and weak areas.
*   **Daily Goals:** Tracks your solved problems and keeps you consistent.
*   **Visual Feedback:** Modern, dark-themed dashboard aimed at productivity.

## 🔌 For Developers and Contributors

This repository contains the full source code for the project:

*   `extension/`: The Chrome Extension (Frontend Logic).
*   `frontend/`: The Next.js Web Interface.
*   `app/`: The FastAPI Backend (Hosted on Render).

To contribute or run the backend locally, please refer to the `requirements.txt` file and set up your environment variables.
