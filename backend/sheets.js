import { google } from 'googleapis';
import fs from 'fs';
import dotenv from 'dotenv';

dotenv.config();

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

        // Prepare row data for literary agent information
        const row = [
            new Date(data.timestamp).toLocaleString('de-DE'),
            data.url || data.source_url || '',
            data.agent_name || '',
            data.agency_name || '',
            data.country || '',
            data.website || '',
            data.email || '',
            data.is_open_to_submissions ? 'Ja' : 'Nein',
            data.requires_bio ? 'Ja' : 'Nein',
            data.requires_expose ? 'Ja' : 'Nein',
            data.requires_project_plan ? 'Ja' : 'Nein',
            data.genre_thriller ? 'Ja' : 'Nein',
            data.genre_krimi ? 'Ja' : 'Nein',
            data.genre_romance ? 'Ja' : 'Nein',
            data.genre_fantasy ? 'Ja' : 'Nein',
            data.genre_scifi ? 'Ja' : 'Nein',
            data.genre_historical ? 'Ja' : 'Nein',
            data.genre_contemporary ? 'Ja' : 'Nein',
            data.genre_literary ? 'Ja' : 'Nein',
            data.genre_ya ? 'Ja' : 'Nein',
            data.genre_mg ? 'Ja' : 'Nein',
            data.genre_children ? 'Ja' : 'Nein',
            data.genre_horror ? 'Ja' : 'Nein',
            data.genre_womens_fiction ? 'Ja' : 'Nein',
            data.genre_lgbtq ? 'Ja' : 'Nein',
            data.genre_dystopian ? 'Ja' : 'Nein',
            data.genre_memoir ? 'Ja' : 'Nein',
            data.genre_biography ? 'Ja' : 'Nein',
            data.genre_selfhelp ? 'Ja' : 'Nein',
            data.genre_business ? 'Ja' : 'Nein',
            data.genre_truecrime ? 'Ja' : 'Nein',
            data.confidence_score ? `${data.confidence_score}%` : '0%'
        ];

        // Append to sheet
        await sheets.spreadsheets.values.append({
            spreadsheetId: SPREADSHEET_ID,
            range: 'Sheet1!A:AF', // Updated range for 32 columns
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

        // Create headers for literary agent data
        const headers = [
            'Timestamp',
            'Source URL',
            'Agent Name',
            'Agency Name',
            'Country',
            'Website',
            'Email',
            'Open for Submission',
            'Bio/Vita required',
            'Exposé required',
            'Project Plan required',
            'Thriller',
            'Krimi',
            'Romance',
            'Fantasy',
            'Sci-Fi',
            'Historical',
            'Contemporary',
            'Literary Fiction',
            'Young Adult',
            'Middle Grade',
            'Children',
            'Horror',
            'Women\'s Fiction',
            'LGBTQ+',
            'Dystopian',
            'Memoir',
            'Biography',
            'Self-Help',
            'Business',
            'True Crime',
            'Confidence Score'
        ];

        await sheets.spreadsheets.values.update({
            spreadsheetId: SPREADSHEET_ID,
            range: 'Sheet1!A1:AF1',
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
