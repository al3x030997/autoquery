import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { scrapeUrl } from './scraper.js';
import { extractWithOllama } from './ollama.js';
import { saveToGoogleSheets } from './sheets.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'OK', message: 'Backend is running!' });
});

// Main endpoint: Submit URL
app.post('/api/submit-url', async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({ error: 'URL is required' });
        }

        console.log(`\n📥 Received URL: ${url}`);

        // Step 1: Scrape the URL
        console.log('🔍 Scraping content...');
        const scrapedContent = await scrapeUrl(url);
        console.log(`✅ Scraped ${scrapedContent.text.length} characters`);

        // Step 2: Extract structured data with Ollama
        console.log('🤖 Extracting data with Ollama...');
        const extractedData = await extractWithOllama(scrapedContent);
        console.log('✅ Data extracted:', extractedData);

        // Step 3: Save to Google Sheets
        console.log('💾 Saving to Google Sheets...');
        await saveToGoogleSheets({
            url,
            ...scrapedContent,
            ...extractedData,
            timestamp: new Date().toISOString()
        });
        console.log('✅ Saved to Google Sheets!');

        res.json({
            success: true,
            message: 'URL processed successfully',
            data: {
                url,
                title: scrapedContent.title,
                ...extractedData
            }
        });

    } catch (error) {
        console.error('❌ Error:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`\n🚀 Backend server running on http://localhost:${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/health`);
    console.log(`\n🔧 Make sure:`);
    console.log(`   - Ollama is running (ollama serve)`);
    console.log(`   - Google Sheets credentials are configured`);
    console.log(`\n💡 Ready to receive URLs!\n`);
});
