import axios from 'axios';

const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434';
const MODEL = process.env.OLLAMA_MODEL || 'llama3.2';

/**
 * Extract structured data from content using Ollama
 * @param {Object} content - Content object with title and text
 * @returns {Promise<Object>} Extracted structured data
 */
export async function extractWithOllama(content) {
    try {
        const prompt = `Analyze the following web content and extract structured information.

Title: ${content.title}
Content: ${content.text.substring(0, 4000)}

Extract the following information in JSON format:
{
  "category": "main category (e.g., Technology, Business, News, Blog, etc.)",
  "summary": "brief 2-3 sentence summary",
  "mainTopics": ["topic1", "topic2", "topic3"],
  "sentiment": "positive/neutral/negative",
  "language": "detected language code (en, de, etc.)"
}

Only return valid JSON, nothing else.`;

        console.log(`🤖 Calling Ollama with model: ${MODEL}`);

        const response = await axios.post(`${OLLAMA_URL}/api/generate`, {
            model: MODEL,
            prompt: prompt,
            stream: false,
            options: {
                temperature: 0.3,
                num_predict: 500
            }
        }, {
            timeout: 60000 // 60 second timeout
        });

        const result = response.data.response;

        // Try to parse JSON from the response
        let extractedData;
        try {
            // Remove markdown code blocks if present
            const jsonMatch = result.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                extractedData = JSON.parse(jsonMatch[0]);
            } else {
                throw new Error('No JSON found in response');
            }
        } catch (parseError) {
            console.warn('⚠️ Failed to parse JSON from Ollama, using defaults');
            extractedData = {
                category: 'Unknown',
                summary: result.substring(0, 200),
                mainTopics: [],
                sentiment: 'neutral',
                language: 'en'
            };
        }

        return extractedData;

    } catch (error) {
        console.error('❌ Ollama error:', error.message);

        // Return default values if Ollama fails
        return {
            category: 'Error',
            summary: 'Failed to extract summary',
            mainTopics: [],
            sentiment: 'neutral',
            language: 'unknown',
            error: error.message
        };
    }
}

/**
 * Check if Ollama is running and the model is available
 */
export async function checkOllama() {
    try {
        const response = await axios.get(`${OLLAMA_URL}/api/tags`);
        const models = response.data.models || [];
        const modelExists = models.some(m => m.name.includes(MODEL));

        return {
            running: true,
            modelAvailable: modelExists,
            availableModels: models.map(m => m.name)
        };
    } catch (error) {
        return {
            running: false,
            error: error.message
        };
    }
}
