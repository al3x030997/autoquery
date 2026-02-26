import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434';
const EMBED_MODEL = process.env.EMBED_MODEL || 'nomic-embed-text';
const REGISTRY_PATH = path.join(__dirname, 'data', 'genre-registry.json');

// Similarity thresholds (configurable via .env)
const MATCH_THRESHOLD = parseFloat(process.env.GENRE_MATCH_THRESHOLD || '0.82');

/**
 * Load the genre registry from disk
 */
export function loadRegistry() {
    try {
        if (!fs.existsSync(REGISTRY_PATH)) return null;
        return JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    } catch (error) {
        console.error(`Failed to load genre registry: ${error.message}`);
        return null;
    }
}

/**
 * Save registry to disk (atomic write)
 */
export function saveRegistry(registry) {
    registry.last_updated = new Date().toISOString();
    const tmpPath = REGISTRY_PATH + '.tmp';
    fs.writeFileSync(tmpPath, JSON.stringify(registry, null, 2));
    fs.renameSync(tmpPath, REGISTRY_PATH);
}

/**
 * Get embedding vector from Ollama
 */
export async function getEmbedding(text) {
    const response = await axios.post(`${OLLAMA_URL}/api/embed`, {
        model: EMBED_MODEL,
        input: text
    }, { timeout: 10000 });
    return response.data.embeddings[0];
}

/**
 * Cosine similarity between two vectors
 */
export function cosineSimilarity(a, b) {
    let dot = 0, magA = 0, magB = 0;
    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        magA += a[i] * a[i];
        magB += b[i] * b[i];
    }
    const mag = Math.sqrt(magA) * Math.sqrt(magB);
    return mag === 0 ? 0 : dot / mag;
}

/**
 * Normalize genre text for comparison
 */
function normalize(text) {
    return text.toLowerCase().trim()
        .replace(/\b(the|a|an)\b/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Initialize registry with seed genres (one-time cold start)
 * seedGenres is a flat array of genre names
 */
export async function initializeRegistry(seedGenres) {
    console.log(`\n🌱 Initializing genre registry with ${seedGenres.length} seed genres...`);
    const registry = {
        version: 2,
        embedding_model: EMBED_MODEL,
        last_updated: new Date().toISOString(),
        genres: []
    };

    for (const name of seedGenres) {
        try {
            const embedding = await getEmbedding(name);
            registry.genres.push({
                name,
                embedding,
                aliases: [],
                added: new Date().toISOString(),
                source: 'seed'
            });
        } catch (error) {
            console.error(`   Failed to embed "${name}": ${error.message}`);
            registry.genres.push({
                name,
                embedding: null,
                aliases: [],
                added: new Date().toISOString(),
                source: 'seed'
            });
        }
    }

    console.log(`✅ Genre registry initialized: ${registry.genres.length} genres`);
    saveRegistry(registry);
    return registry;
}

/**
 * Find best matching genre in registry for a raw genre string
 */
export async function findBestMatch(rawGenre, registry) {
    const normalized = normalize(rawGenre);
    if (!normalized) return { match: null, similarity: 0, rawGenre };

    // Quick check: exact name or alias match
    for (const genre of registry.genres) {
        if (normalize(genre.name) === normalized) {
            return { match: genre.name, similarity: 1.0, rawGenre };
        }
        if (genre.aliases.some(a => normalize(a) === normalized)) {
            return { match: genre.name, similarity: 1.0, rawGenre };
        }
    }

    // Substring check: "Crime Fiction" contains "Crime"
    for (const genre of registry.genres) {
        const genreNorm = normalize(genre.name);
        if (normalized.includes(genreNorm) || genreNorm.includes(normalized)) {
            return { match: genre.name, similarity: 0.95, rawGenre };
        }
    }

    // Embedding similarity
    let embedding;
    try {
        embedding = await getEmbedding(rawGenre);
    } catch (error) {
        console.log(`   Failed to embed "${rawGenre}": ${error.message}`);
        return { match: null, similarity: 0, rawGenre };
    }

    let bestMatch = null;
    let bestSimilarity = 0;

    for (const genre of registry.genres) {
        if (!genre.embedding) continue;
        const sim = cosineSimilarity(embedding, genre.embedding);
        if (sim > bestSimilarity) {
            bestSimilarity = sim;
            bestMatch = genre.name;
        }
    }

    return {
        match: bestSimilarity >= MATCH_THRESHOLD ? bestMatch : null,
        bestMatch,
        similarity: Math.round(bestSimilarity * 100) / 100,
        rawGenre
    };
}

/**
 * Classify raw genre text using embeddings
 * Returns { genres: [], unmatched: [] }
 */
export async function classifyGenresWithEmbeddings(genresRaw, registry) {
    const genres = [];
    const unmatched = [];

    const rawGenres = genresRaw.split(/[,;]+/)
        .map(g => g.trim())
        .filter(g => g.length > 1);

    const skipTerms = ['fiction', 'nonfiction', 'non-fiction', 'books', 'novels', 'literature'];
    const seen = new Set();

    for (const raw of rawGenres) {
        if (skipTerms.includes(normalize(raw))) continue;

        const result = await findBestMatch(raw, registry);

        if (result.match && !seen.has(result.match)) {
            seen.add(result.match);
            genres.push(result.match);
        } else if (!result.match && result.bestMatch) {
            unmatched.push({
                raw,
                bestMatch: result.bestMatch,
                similarity: result.similarity
            });
        }
    }

    // Anti-spam: cap unmatched at 5
    if (unmatched.length > 5) {
        console.log(`   ⚠️ ${unmatched.length} unmatched genres — keeping top 5`);
        unmatched.sort((a, b) => a.similarity - b.similarity);
        unmatched.length = 5;
    }

    return { genres, unmatched };
}

/**
 * Add a new genre to the registry (user-approved)
 */
export async function addGenreToRegistry(registry, genreName) {
    const embedding = await getEmbedding(genreName);
    registry.genres.push({
        name: genreName,
        embedding,
        aliases: [],
        added: new Date().toISOString(),
        source: 'user'
    });
    saveRegistry(registry);
    console.log(`✅ New genre added to registry: "${genreName}"`);
    return registry;
}

/**
 * Get genre names from registry as flat array
 */
export function getRegistryGenres(registry) {
    return registry.genres.map(g => g.name);
}

/**
 * Check if the embedding model is available
 */
export async function checkEmbeddingModel() {
    try {
        await axios.post(`${OLLAMA_URL}/api/embed`, {
            model: EMBED_MODEL,
            input: 'test'
        }, { timeout: 5000 });
        return true;
    } catch {
        return false;
    }
}
