# AutoQuery Backend - URL to Database

Backend for scraping URLs, extracting data with Ollama (local LLM), and storing in Google Sheets.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
npm install
```

### 2. Install & Setup Ollama

```bash
# Install Ollama (if not installed)
brew install ollama

# Start Ollama service
ollama serve

# In a new terminal, pull the model
ollama pull llama3.2
# Or use mistral: ollama pull mistral
```

### 3. Setup Google Sheets

#### A. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Google Sheets API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

#### B. Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Name it (e.g., "autoquery-sheets")
4. Click "Create and Continue"
5. Skip optional steps, click "Done"

#### C. Create Key

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Select "JSON"
5. Save the file as `google-credentials.json` in the `backend/` folder

#### D. Create & Share Spreadsheet

1. Create a new Google Sheet: [sheets.google.com](https://sheets.google.com)
2. Name it (e.g., "AutoQuery Data")
3. Copy the Spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```
4. **IMPORTANT:** Share the sheet with the service account email:
   - Click "Share" button
   - Paste the service account email (from the JSON file: `client_email`)
   - Give "Editor" access
   - Click "Send"

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Spreadsheet ID
nano .env
```

Add your Google Sheet ID:
```env
GOOGLE_SHEET_ID=your-actual-spreadsheet-id
```

### 5. Initialize Google Sheet (Optional)

Run this once to add headers to your sheet:

```bash
node -e "import('./sheets.js').then(m => m.initializeSheet())"
```

### 6. Start the Server

```bash
npm start

# Or use watch mode for development
npm run dev
```

You should see:
```
🚀 Backend server running on http://localhost:3000
📊 Health check: http://localhost:3000/health
```

## 🧪 Test the API

### Test with curl:

```bash
curl -X POST http://localhost:3000/api/submit-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Or use the frontend:
Open your browser to the app: `http://localhost:8080/app/` (or your GitHub Pages URL)

## 📁 Project Structure

```
backend/
├── server.js          # Express server & API endpoints
├── scraper.js         # Web scraping with Cheerio
├── ollama.js          # Ollama LLM integration
├── sheets.js          # Google Sheets integration
├── package.json       # Dependencies
├── .env               # Configuration (create from .env.example)
└── google-credentials.json  # Google service account key (you create this)
```

## 🔧 Troubleshooting

### Ollama not responding
```bash
# Check if Ollama is running
ollama list

# Start Ollama
ollama serve
```

### Google Sheets permission denied
- Make sure you shared the sheet with the service account email
- Check that the service account has "Editor" access

### Model not found
```bash
# List available models
ollama list

# Pull the model
ollama pull llama3.2
```

## 📊 Google Sheet Columns

| Column | Description |
|--------|-------------|
| Timestamp | When the URL was processed |
| URL | Original URL |
| Title | Page title |
| Category | AI-extracted category |
| Summary | AI-generated summary |
| Main Topics | Key topics found |
| Sentiment | Positive/Neutral/Negative |
| Language | Detected language |
| Word Count | Number of words scraped |

## 🎯 Next Steps

- Test with different URLs
- Adjust Ollama prompt in `ollama.js` for better extraction
- Add more columns to the sheet
- Deploy backend to a server (Railway, Render, etc.)

## ⚙️ Configuration

### Change Ollama Model

Edit `.env`:
```env
OLLAMA_MODEL=mistral
# or
OLLAMA_MODEL=llama3.1
```

### Change Port

Edit `.env`:
```env
PORT=3001
```

## 🚀 Ready!

Your backend is now ready to receive URLs, scrape content, extract data with Ollama, and save to Google Sheets!

Test it from the frontend: `https://al3x030997.github.io/autoquery/app/`
