# CP Coach Chrome Extension

A minimal Chrome extension for getting competitive programming problem recommendations.

## Features

- Quick access to personalized problem recommendations
- Remembers your Codeforces handle
- One-click to open problems on Codeforces

## Installation

1. Open Chrome and go to `chrome://extensions`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select this `extension` folder

## Usage

1. Click the CP Coach extension icon
2. Enter your Codeforces handle (saved for next time)
3. Select a topic (DP, Graphs, etc.)
4. Click **Get Next Problem**
5. Click the green button to solve on Codeforces

## Requirements

- Backend server running on `http://127.0.0.1:8080`
- Valid Codeforces handle

## Files

```
extension/
├── manifest.json   # Extension configuration
├── popup.html      # Popup UI
├── popup.css       # Styles
├── popup.js        # Logic
└── icons/          # Extension icons
```

## Backend API

The extension calls:
```
GET /extension/recommend?handle={handle}&topic={topic}
```

## Troubleshooting

- **"Backend not reachable"**: Start the backend server
- **"User not found"**: The handle will be registered automatically
- **No problems**: Try a different topic
