import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { crawlForAgents } from './crawler.js';
import { saveToGoogleSheets } from './sheets.js';
import { loadRegistry, addGenreToRegistry, checkEmbeddingModel } from './genre-registry.js';
import { invalidateGenreCache } from './ollama.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Serve frontend files
// Root serves the landing page (index.html from project root)
// App files (agent finder, review) are under /app/
app.use('/app', express.static(path.join(__dirname, '..', 'app')));
app.use(express.static(path.join(__dirname, '..')));

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

// Endpoint 4: Get current genre registry
app.get('/api/genres', async (req, res) => {
    try {
        const registry = loadRegistry();
        if (!registry) {
            return res.json({ fiction: [], nonfiction: [], total: 0, initialized: false });
        }
        res.json({
            fiction: registry.genres.fiction.map(g => ({ name: g.name, source: g.source, added: g.added })),
            nonfiction: registry.genres.nonfiction.map(g => ({ name: g.name, source: g.source, added: g.added })),
            total: registry.genres.fiction.length + registry.genres.nonfiction.length,
            initialized: true
        });
    } catch (error) {
        console.error('❌ Error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Endpoint 5: Approve a new genre (add to registry)
app.post('/api/genres/approve', async (req, res) => {
    try {
        const { genreName, category } = req.body;
        if (!genreName || !['fiction', 'nonfiction'].includes(category)) {
            return res.status(400).json({ error: 'genreName and category (fiction/nonfiction) required' });
        }

        let registry = loadRegistry();
        if (!registry) {
            return res.status(400).json({ error: 'Genre registry not initialized yet' });
        }

        // Check for duplicates
        const exists = registry.genres[category].some(
            g => g.name.toLowerCase() === genreName.toLowerCase()
        );
        if (exists) {
            return res.json({ success: true, message: 'Genre already exists', genre: genreName });
        }

        registry = await addGenreToRegistry(registry, genreName, category);
        invalidateGenreCache();

        console.log(`✅ New genre approved: "${genreName}" (${category})`);
        res.json({ success: true, genre: genreName, category });
    } catch (error) {
        console.error('❌ Error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`\n🚀 Backend server running on http://localhost:${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/health`);
    console.log(`\n🔧 Make sure:`);
    console.log(`   - Ollama is running (ollama serve)`);
    console.log(`   - Google Sheets credentials are configured`);

    // Check embedding model availability
    checkEmbeddingModel().then(available => {
        if (available) {
            console.log(`   - Embedding model ready`);
        } else {
            console.log(`   ⚠️  Embedding model not found. Run: ollama pull nomic-embed-text`);
        }
        console.log(`\n💡 Ready to crawl agent websites!\n`);
    });
});
