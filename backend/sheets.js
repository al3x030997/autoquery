import { google } from 'googleapis';
import fs from 'fs';

const SPREADSHEET_ID = process.env.GOOGLE_SHEET_ID;
const CREDENTIALS_PATH = process.env.GOOGLE_CREDENTIALS_PATH || './google-credentials.json';

/**
 * Save data to Google Sheets
 * @param {Object} data - Data to save
 */
export async function saveToGoogleSheets(data) {
    try {
        // Check if credentials exist
        if (!fs.existsSync(CREDENTIALS_PATH)) {
            throw new Error(`Google credentials not found at ${CREDENTIALS_PATH}`);
        }

        if (!SPREADSHEET_ID) {
            throw new Error('GOOGLE_SHEET_ID not set in .env file');
        }

        // Load credentials
        const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));

        // Authenticate
        const auth = new google.auth.GoogleAuth({
            credentials,
            scopes: ['https://www.googleapis.com/auth/spreadsheets']
        });

        const sheets = google.sheets({ version: 'v4', auth });

        // Prepare row data
        const row = [
            new Date(data.timestamp).toLocaleString('de-DE'),
            data.url,
            data.title,
            data.category || '',
            data.summary || '',
            (data.mainTopics || []).join(', '),
            data.sentiment || '',
            data.language || '',
            data.wordCount || 0
        ];

        // Append to sheet
        await sheets.spreadsheets.values.append({
            spreadsheetId: SPREADSHEET_ID,
            range: 'Sheet1!A:I', // Adjust if your sheet has a different name
            valueInputOption: 'USER_ENTERED',
            requestBody: {
                values: [row]
            }
        });

        console.log('✅ Successfully saved to Google Sheets');

    } catch (error) {
        throw new Error(`Failed to save to Google Sheets: ${error.message}`);
    }
}

/**
 * Initialize Google Sheet with headers
 */
export async function initializeSheet() {
    try {
        if (!fs.existsSync(CREDENTIALS_PATH)) {
            throw new Error(`Google credentials not found at ${CREDENTIALS_PATH}`);
        }

        const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
        const auth = new google.auth.GoogleAuth({
            credentials,
            scopes: ['https://www.googleapis.com/auth/spreadsheets']
        });

        const sheets = google.sheets({ version: 'v4', auth });

        // Create headers
        const headers = [
            'Timestamp',
            'URL',
            'Title',
            'Category',
            'Summary',
            'Main Topics',
            'Sentiment',
            'Language',
            'Word Count'
        ];

        await sheets.spreadsheets.values.update({
            spreadsheetId: SPREADSHEET_ID,
            range: 'Sheet1!A1:I1',
            valueInputOption: 'USER_ENTERED',
            requestBody: {
                values: [headers]
            }
        });

        console.log('✅ Sheet initialized with headers');

    } catch (error) {
        throw new Error(`Failed to initialize sheet: ${error.message}`);
    }
}
