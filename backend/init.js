import dotenv from 'dotenv';
import { initializeSheet } from './sheets.js';

dotenv.config();

console.log('🔍 GOOGLE_SHEET_ID:', process.env.GOOGLE_SHEET_ID);
console.log('🔍 CREDENTIALS_PATH:', process.env.GOOGLE_CREDENTIALS_PATH);

if (!process.env.GOOGLE_SHEET_ID) {
    console.error('❌ GOOGLE_SHEET_ID is not set!');
    process.exit(1);
}

initializeSheet()
    .then(() => {
        console.log('✅ Sheet initialized successfully!');
        process.exit(0);
    })
    .catch(err => {
        console.error('❌ Error:', err.message);
        process.exit(1);
    });
