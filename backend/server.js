import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { crawlForAgents } from './crawler.js';
import { saveToGoogleSheets } from './sheets.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Serve frontend files
app.use(express.static(path.join(__dirname, '..', 'app')));

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'OK', message: 'Backend is running!' });
});

// Endpoint 1: Extract agents (no saving yet)
app.post('/api/extract', async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({ error: 'URL is required' });
        }

        console.log(`\n📥 Extracting from URL: ${url}`);

        // Crawl for all agents
        console.log('🕷️  Crawling for agents...');
        const result = await crawlForAgents(url);

        // Check if we got a warning (too many links)
        if (result.warning) {
            console.log(`⚠️  Warning: ${result.message}`);
            return res.json({
                success: false,
                warning: true,
                ...result
            });
        }

        // Normal response with agents
        console.log(`✅ Found ${result.length} agents`);
        res.json({
            success: true,
            agentsFound: result.length,
            agents: result
        });

    } catch (error) {
        console.error('❌ Error:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Endpoint 2: Crawl URLs with mode selection (single or dynamic)
app.post('/api/crawl', async (req, res) => {
    try {
        const { urls, mode } = req.body;

        if (!urls || !Array.isArray(urls) || urls.length === 0) {
            return res.status(400).json({ error: 'URLs array is required' });
        }

        if (!mode || !['single', 'dynamic'].includes(mode)) {
            return res.status(400).json({ error: 'Mode must be "single" or "dynamic"' });
        }

        console.log(`\n📥 Crawl request: ${mode} mode, ${urls.length} URL(s)`);

        let allAgents = [];

        if (mode === 'single') {
            // Single URL mode: Crawl each URL independently, no link discovery
            console.log('🎯 Single URL Mode: Crawling each URL independently...');

            for (const url of urls) {
                console.log(`\n🔗 Processing: ${url}`);
                try {
                    const result = await crawlForAgents(url, { singleUrlMode: true });

                    // Check if we got a warning
                    if (result.warning) {
                        console.log(`⚠️  Warning for ${url}: ${result.message}`);
                        continue;
                    }

                    // Collect agents
                    if (Array.isArray(result)) {
                        allAgents = allAgents.concat(result);
                        console.log(`   ✅ Found ${result.length} agent(s)`);
                    }
                } catch (error) {
                    console.error(`   ❌ Error crawling ${url}: ${error.message}`);
                    // Continue with next URL
                }
            }

        } else {
            // Dynamic mode: Use first URL for link discovery
            console.log('🌐 Dynamic Mode: Using intelligent link discovery...');
            const baseUrl = urls[0];
            console.log(`\n🔗 Base URL: ${baseUrl}`);

            const result = await crawlForAgents(baseUrl, { singleUrlMode: false });

            // Check if we got a warning
            if (result.warning) {
                console.log(`⚠️  Warning: ${result.message}`);
                return res.json({
                    success: false,
                    warning: true,
                    ...result
                });
            }

            allAgents = result;
        }

        console.log(`\n✅ Total agents found: ${allAgents.length}`);

        res.json({
            success: true,
            mode: mode,
            urlsProcessed: mode === 'single' ? urls.length : 1,
            agentsFound: allAgents.length,
            agents: allAgents
        });

    } catch (error) {
        console.error('❌ Error:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Endpoint 3: Save approved agents to Google Sheets
app.post('/api/save', async (req, res) => {
    try {
        const { agents } = req.body;

        if (!agents || !Array.isArray(agents)) {
            return res.status(400).json({ error: 'Agents array is required' });
        }

        console.log(`\n💾 Saving ${agents.length} approved agents to Google Sheets...`);
        const timestamp = new Date().toISOString();
        const saved = [];
        const failed = [];

        for (const agent of agents) {
            try {
                await saveToGoogleSheets({
                    url: agent.source_url,
                    ...agent,
                    timestamp
                });
                console.log(`✅ Saved: ${agent.agent_name}`);
                saved.push(agent.agent_name);
            } catch (error) {
                console.error(`❌ Error saving ${agent.agent_name}: ${error.message}`);
                failed.push({ name: agent.agent_name, error: error.message });
            }
        }

        console.log(`✅ Saved ${saved.length} agents!`);

        res.json({
            success: true,
            saved: saved.length,
            failed: failed.length,
            savedAgents: saved,
            failedAgents: failed
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
    console.log(`\n✨ NEW Features (v2.0):`);
    console.log(`   - 🧠 Chain of Thought: Step-by-step reasoning for better extraction`);
    console.log(`   - 📚 Adaptive Extraction: Reuses agency-wide fields (50% faster!)`);
    console.log(`   - 🎯 Evidence Tracking: Shows source quotes for all extracted fields`);
    console.log(`   - 🔍 No URL filtering: Crawls first 25 pages from sitemap/links`);
    console.log(`   - 📊 Self-Consistency: 2x extraction per page (cost-optimized)`);
    console.log(`   - 🌍 Auto-detect country from Impressum`);
    console.log(`   - 🇩🇪 German genre mapping & negative formulations`);
    console.log(`\n💡 Ready to crawl agent websites!\n`);
});
