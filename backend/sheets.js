import { google } from 'googleapis';
import fs from 'fs';
import dotenv from 'dotenv';

dotenv.config();

const SPREADSHEET_ID = process.env.GOOGLE_SHEET_ID;
const CREDENTIALS_PATH = process.env.GOOGLE_CREDENTIALS_PATH || './google-credentials.json';

/**
 * Get authenticated Google Sheets client
 */
function getSheetsClient() {
    if (!fs.existsSync(CREDENTIALS_PATH)) {
        throw new Error(`Google credentials not found at ${CREDENTIALS_PATH}`);
    }
    if (!SPREADSHEET_ID) {
        throw new Error('GOOGLE_SHEET_ID not set in .env file');
    }

    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
    const auth = new google.auth.GoogleAuth({
        credentials,
        scopes: ['https://www.googleapis.com/auth/spreadsheets']
    });

    return google.sheets({ version: 'v4', auth });
}

/**
 * Save data to Google Sheets
 */
export async function saveToGoogleSheets(data) {
    try {
        const sheets = getSheetsClient();

        const row = [
            new Date(data.timestamp).toLocaleString('de-DE'),
            data.url || data.source_url || '',
            data.agent_name || '',
            data.agency_name || '',
            data.agent_role || '',
            data.country || '',
            data.email || '',
            data.submission_url || '',
            data.is_open_to_submissions ? 'Ja' : 'Nein',
            (data.accepted_genres_fiction || []).join(', '),
            (data.accepted_genres_nonfiction || []).join(', '),
            (data.hard_nos || []).join(', '),
            (data.audience || []).join(', '),
            data.manuscript_wishlist_summary || '',
            (data.specific_keywords || []).join(', '),
            data.requires_bio ? 'Ja' : 'Nein',
            data.requires_expose ? 'Ja' : 'Nein',
            data.requires_manuscript ? 'Ja' : 'Nein',
            data.estimated_response_time || '',
            data.confidence_score ? `${data.confidence_score}%` : '0%'
        ];

        await sheets.spreadsheets.values.append({
            spreadsheetId: SPREADSHEET_ID,
            range: 'Sheet1!A:T',
            valueInputOption: 'USER_ENTERED',
            requestBody: { values: [row] }
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
        const sheets = getSheetsClient();

        const headers = [
            'Timestamp',
            'Source URL',
            'Agent Name',
            'Agency Name',
            'Role',
            'Country',
            'Email',
            'Submission URL',
            'Open for Submissions',
            'Fiction Genres',
            'Nonfiction Genres',
            'Hard Nos',
            'Audience',
            'Wishlist Summary',
            'Keywords',
            'Bio required',
            'Expose required',
            'Manuscript required',
            'Response Time',
            'Confidence Score'
        ];

        await sheets.spreadsheets.values.update({
            spreadsheetId: SPREADSHEET_ID,
            range: 'Sheet1!A1:T1',
            valueInputOption: 'USER_ENTERED',
            requestBody: { values: [headers] }
        });

        console.log('✅ Sheet initialized with headers');

    } catch (error) {
        throw new Error(`Failed to initialize sheet: ${error.message}`);
    }
}
