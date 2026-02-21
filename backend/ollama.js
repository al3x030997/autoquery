import axios from 'axios';

const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434';
const MODEL = process.env.OLLAMA_MODEL || 'llama3.2';

// Genre categories matching manuscriptwishlist.com exactly
const GENRE_CATEGORIES = {
    fiction: [
        'Action/Adventure', 'BIPOC Crime Fiction', 'BIPOC Literature', 'BIPOC Mystery',
        'BIPOC Thriller', 'Bookclub', 'Caribbean Literature', 'Children\'s',
        'Commercial', 'Contemporary', 'Crime', 'CyberPunk',
        'Domestic Thriller', 'East Asian Literature', 'Eco-Fiction', 'Erotica',
        'Family Saga', 'Fantasy', 'Folklore', 'General',
        'Gothic', 'Graphic Novel', 'Historical', 'Horror',
        'Humor', 'LGBTQ', 'Literary', 'Magical Realism',
        'Middle Grade', 'Military', 'Mystery', 'Neo-Western',
        'New Adult', 'Picture Books', 'Poetry', 'Psychological Thriller',
        'Religious', 'Romance', 'Romcom', 'Science Fiction',
        'Short Story', 'South Asian Literature', 'South East Asian Literature',
        'Speculative', 'Speculative Literary', 'Sports', 'Steampunk',
        'Thriller', 'Upmarket', 'West African Literature', 'Western',
        'Women\'s Fiction', 'Young Adult'
    ],
    nonfiction: [
        'Art', 'Bible Studies', 'Biography', 'Business',
        'Cookbooks', 'Crafts/DIY', 'Cultural criticism', 'Current Events',
        'Fashion', 'Feminism and women\'s issues', 'Fitness', 'Health',
        'History', 'Humor', 'Illustrated', 'Journalism',
        'LGBTQ', 'Memoir', 'Parenting', 'Pop Culture',
        'Psychology', 'Relationships and family', 'Science', 'Self-help',
        'Spiritual', 'Sports', 'Tarot/Astrology', 'Travel',
        'True Crime', 'Wellness', 'Witches/Witchcraft'
    ]
};

// Audience / Age Group categories
const AUDIENCE_CATEGORIES = [
    'Adult', 'Middle Grade', 'New Adult', 'Other Children\'s', 'Picture Book', 'Young Adult'
];

/**
 * Phase 1: Extract agent info + free-text genres, hard_nos, audience from content
 * Lean prompt — no genre list, no classification
 */
async function extractAgentInfo(content, temperature = 0.0, knownFields = null) {
    const submissionUrls = (content.links || [])
        .filter(link => /submit|query|manuscript|querymanager|submittable/i.test(link))
        .slice(0, 10)
        .join('\n');

    let knownFieldsSection = '';
    if (knownFields && Object.keys(knownFields).length > 0) {
        knownFieldsSection = `\n ALREADY KNOWN (use these, do NOT re-extract):\n`;
        Object.entries(knownFields).forEach(([key, value]) => {
            if (value && value !== 'Unknown' && value !== '') {
                knownFieldsSection += `  - ${key}: "${value}"\n`;
            }
        });
        knownFieldsSection += `\nFocus on extracting ONLY the MISSING fields.\n\n`;
    }

    const prompt = `You are a data extraction assistant. Extract ALL literary agent information from this webpage. Be thorough — capture every detail.

Title: ${content.title}
Content: ${content.text.substring(0, 50000)}

${submissionUrls ? `Submission-related URLs found:\n${submissionUrls}\n` : ''}
${knownFieldsSection}

RULES:
- Extract ONLY what is EXPLICITLY stated in the text
- Use "Unknown" if not found, false for booleans, [] for arrays, "" for strings
- genres_raw: list ALL genres/categories the agent represents. Look EVERYWHERE — main content, sidebars, tags, labels, genre lists. Include Fiction AND Nonfiction. Be comprehensive — list every genre mentioned.
- hard_nos_raw: list everything they explicitly do NOT want or are NOT looking for (e.g. "NOT looking for rhyming books", "no sci-fi", "NOT currently looking for X")
- audience_raw: list all age groups/audiences mentioned (e.g. "Adult", "Middle Grade", "Young Adult", "Picture Book", "Children's")
- manuscript_wishlist_summary: capture the FULL wishlist with ALL specific interests, themes, and preferences. Include bullet points, specific book types, and detailed preferences.
- contact_email: look for email addresses in submission guidelines (e.g. "email to x@y.com", "send your query to x@y.com")
- specific_keywords: extract specific themes, tropes, interests (e.g. "queer representation", "marginalized identities", "clever humor", "voice-driven")

Output ONLY this JSON:

{
  "agent_name": "full name",
  "agent_name_evidence": "exact quote",
  "agency_name": "agency name",
  "agency_name_evidence": "exact quote",
  "agent_role": "role/title (e.g. Agent, Literary Agent, Associate Literary Agent)",
  "contact_email": "email address for submissions",
  "submission_url": "URL for submissions",
  "is_open_to_submissions": true/false,
  "is_open_to_submissions_evidence": "exact quote",
  "status_notice": "submission status notice",
  "estimated_response_time": "response time",
  "genres_raw": "ALL genres, exactly as listed on the page, separated by commas",
  "hard_nos_raw": "everything they do NOT want, exactly as written",
  "audience_raw": "all age groups/audiences mentioned, separated by commas",
  "manuscript_wishlist_summary": "comprehensive summary of what they are looking for",
  "target_audience": "target audience description",
  "specific_keywords": ["keyword1", "keyword2", "keyword3"],
  "requires_bio": true/false,
  "requires_expose": true/false,
  "requires_manuscript": true/false
}

START with { and END with }. No explanations.`;

    console.log(`\n📄 Phase 1: Extracting agent info...`);
    console.log(`   Text length: ${content.text.length} chars`);

    const response = await axios.post(`${OLLAMA_URL}/api/generate`, {
        model: MODEL,
        prompt: prompt,
        stream: false,
        options: {
            temperature: temperature,
            num_predict: 4000,
            top_p: 0.1,
            repeat_penalty: 1.2,
            num_ctx: 16384
        },
        keep_alive: 0
    }, {
        timeout: 120000
    });

    const result = response.data.response;
    console.log(`   Raw response (first 500 chars): ${result.substring(0, 500)}`);

    const jsonMatch = result.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
        throw new Error('Phase 1: No JSON found in LLM response');
    }

    let data;
    try {
        data = JSON.parse(jsonMatch[0]);
    } catch (parseError) {
        let fixed = jsonMatch[0];
        // Fix arrays where strings were expected
        fixed = fixed.replace(/"(genres_raw|hard_nos_raw|audience_raw)"\s*:\s*\[([^\]]*)\]/g, (_match, key, items) => {
            const flat = items.replace(/"/g, '').trim();
            return `"${key}": "${flat.replace(/\n/g, ' ')}"`;
        });
        fixed = fixed.replace(/,\s*}/g, '}');
        try {
            data = JSON.parse(fixed);
            console.log(`   Fixed malformed JSON from LLM`);
        } catch (e) {
            throw new Error(`Phase 1: Failed to parse LLM JSON: ${parseError.message}`);
        }
    }

    // Ensure raw fields are strings
    for (const field of ['genres_raw', 'hard_nos_raw', 'audience_raw']) {
        if (Array.isArray(data[field])) {
            data[field] = data[field].join(', ');
        }
        if (!data[field]) data[field] = '';
    }

    console.log(`   Agent: ${data.agent_name}, Agency: ${data.agency_name}`);
    console.log(`   Genres raw: ${data.genres_raw}`);
    console.log(`   Hard nos raw: ${data.hard_nos_raw}`);
    console.log(`   Audience raw: ${data.audience_raw}`);

    return data;
}

/**
 * Phase 2a: Classify free-text genres into standard categories
 * Focused LLM call — only genres, nothing else
 */
async function classifyGenres(genresRaw) {
    if (!genresRaw || genresRaw === 'Unknown' || genresRaw.trim() === '') {
        console.log(`   Phase 2a: No genres to classify`);
        return { fiction: [], nonfiction: [] };
    }

    const prompt = `Classify these literary genres into our standard categories. Be thorough — match as many as apply.

Agent's genres (raw text): "${genresRaw}"

Available FICTION categories:
${GENRE_CATEGORIES.fiction.join(', ')}

Available NONFICTION categories:
${GENRE_CATEGORIES.nonfiction.join(', ')}

Rules:
- Match each mentioned genre to the CLOSEST category from our lists. Include ALL that apply.
- Map terms: "Thriller" → Thriller, "Crime Fiction" → Crime, "Romantic Comedy" → Romcom, "Sci-Fi" → Science Fiction, "MG" → Middle Grade, "YA" → Young Adult, "PB" → Picture Books, "GN" → Graphic Novel, "Kidlit" → Children's
- Map German: Krimi → Crime, Liebesroman → Romance, Ratgeber → Self-help, Biografie → Biography, Historischer Roman → Historical
- "BIPOC" genres: map specific ones (e.g. "Caribbean Literature" → Caribbean Literature), general "BIPOC" → BIPOC Literature
- Only use exact category names from the lists above
- Skip overly generic terms (Fiction, Nonfiction, Books)

Output ONLY this JSON:
{"fiction": ["Category1", "Category2"], "nonfiction": ["Category1"]}`;

    console.log(`\n   Phase 2a: Classifying genres...`);

    const response = await axios.post(`${OLLAMA_URL}/api/generate`, {
        model: MODEL,
        prompt: prompt,
        stream: false,
        options: {
            temperature: 0.0,
            num_predict: 800,
            top_p: 0.1,
            num_ctx: 4096
        },
        keep_alive: 0
    }, {
        timeout: 30000
    });

    const result = response.data.response;
    const jsonMatch = result.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
        console.log(`   Phase 2a: Failed to parse, returning empty`);
        return { fiction: [], nonfiction: [] };
    }

    const classified = JSON.parse(jsonMatch[0]);
    classified.fiction = (classified.fiction || []).filter(g => GENRE_CATEGORIES.fiction.includes(g));
    classified.nonfiction = (classified.nonfiction || []).filter(g => GENRE_CATEGORIES.nonfiction.includes(g));

    console.log(`   Fiction: ${JSON.stringify(classified.fiction)}`);
    console.log(`   Nonfiction: ${JSON.stringify(classified.nonfiction)}`);

    return classified;
}

/**
 * Phase 2b: Classify hard_nos into standard categories
 * Focused LLM call — only rejections, nothing else
 */
async function classifyHardNos(hardNosRaw) {
    if (!hardNosRaw || hardNosRaw === 'Unknown' || hardNosRaw.trim() === '') {
        console.log(`   Phase 2b: No hard_nos to classify`);
        return [];
    }

    const allCategories = [...GENRE_CATEGORIES.fiction, ...GENRE_CATEGORIES.nonfiction];

    const prompt = `Classify these REJECTED/EXCLUDED genres into our standard categories.

Agent does NOT want (raw text): "${hardNosRaw}"

Available categories:
${allCategories.join(', ')}

Rules:
- Match each rejected item to the CLOSEST category. Include ALL that apply.
- Map terms: "rhyming books" → Poetry, "Sci-Fi" → Science Fiction
- Map German: Lyrik → Poetry, Ratgeber → Self-help
- Only use exact category names from the list above
- Include ALL items that are explicitly excluded

Output ONLY this JSON:
{"hard_nos": ["Category1", "Category2"]}`;

    console.log(`\n   Phase 2b: Classifying hard_nos...`);

    const response = await axios.post(`${OLLAMA_URL}/api/generate`, {
        model: MODEL,
        prompt: prompt,
        stream: false,
        options: {
            temperature: 0.0,
            num_predict: 500,
            top_p: 0.1,
            num_ctx: 2048
        },
        keep_alive: 0
    }, {
        timeout: 30000
    });

    const result = response.data.response;
    const jsonMatch = result.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
        console.log(`   Phase 2b: Failed to parse, returning empty`);
        return [];
    }

    const classified = JSON.parse(jsonMatch[0]);
    const hardNos = classified.hard_nos || [];
    const validHardNos = hardNos.filter(g => allCategories.includes(g));

    console.log(`   Hard nos: ${JSON.stringify(validHardNos)}`);
    return validHardNos;
}

/**
 * Phase 2c: Classify audience/age groups
 * Focused LLM call — only audience, nothing else
 */
async function classifyAudience(audienceRaw, genresRaw) {
    // Combine both sources for better audience detection
    const combined = [audienceRaw, genresRaw].filter(Boolean).join(', ');
    if (!combined || combined.trim() === '') {
        console.log(`   Phase 2c: No audience info to classify`);
        return [];
    }

    const prompt = `Identify the target age groups/audiences for this literary agent.

Raw audience info: "${combined}"

Available audience categories:
${AUDIENCE_CATEGORIES.join(', ')}

Rules:
- Match mentioned age groups to our categories
- Map terms: "Children's" or "Kidlit" → Other Children's, "MG" → Middle Grade, "YA" → Young Adult, "PB" or "Picture Books" → Picture Book, "NA" → New Adult
- If "Adult" books are mentioned (literary fiction, thriller, romance for adults, etc.) → Adult
- If only children's categories are mentioned, do NOT add Adult
- Only use exact category names from the list above

Output ONLY this JSON:
{"audience": ["Category1", "Category2"]}`;

    console.log(`\n   Phase 2c: Classifying audience...`);

    const response = await axios.post(`${OLLAMA_URL}/api/generate`, {
        model: MODEL,
        prompt: prompt,
        stream: false,
        options: {
            temperature: 0.0,
            num_predict: 300,
            top_p: 0.1,
            num_ctx: 2048
        },
        keep_alive: 0
    }, {
        timeout: 30000
    });

    const result = response.data.response;
    const jsonMatch = result.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
        console.log(`   Phase 2c: Failed to parse, returning empty`);
        return [];
    }

    const classified = JSON.parse(jsonMatch[0]);
    const audience = classified.audience || [];
    const validAudience = audience.filter(a => AUDIENCE_CATEGORIES.includes(a));

    console.log(`   Audience: ${JSON.stringify(validAudience)}`);
    return validAudience;
}

/**
 * Map classified genres to boolean fields for Google Sheets
 */
function genresToBooleans(classifiedGenres) {
    const genreMap = {};

    // Build fiction mappings
    for (const genre of GENRE_CATEGORIES.fiction) {
        const key = 'genre_fiction_' + genre.toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
        genreMap[genre] = key;
    }

    // Build nonfiction mappings
    for (const genre of GENRE_CATEGORIES.nonfiction) {
        const key = 'genre_nonfiction_' + genre.toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
        genreMap[genre] = key;
    }

    // Start with all false
    const booleans = {};
    for (const field of Object.values(genreMap)) {
        booleans[field] = false;
    }

    // Set true for accepted genres
    const allAccepted = [...(classifiedGenres.fiction || []), ...(classifiedGenres.nonfiction || [])];
    for (const genre of allAccepted) {
        const field = genreMap[genre];
        if (field) {
            booleans[field] = true;
        }
    }

    return booleans;
}

/**
 * Full 2-phase extraction pipeline
 * Phase 1: Agent info + raw genres/hard_nos/audience (1 LLM call)
 * Phase 2a: Genre classification (1 focused LLM call)
 * Phase 2b: Hard_nos classification (1 focused LLM call)
 * Phase 2c: Audience classification (1 focused LLM call)
 * Phase 2a, 2b, 2c run in parallel
 */
export async function extractWithOllama(content, temperature = 0.0, knownFields = null) {
    try {
        // Phase 1: Extract agent info + free-text genres/hard_nos/audience
        const agentInfo = await extractAgentInfo(content, temperature, knownFields);

        // Phase 2a + 2b + 2c: Classify genres, hard_nos, audience IN PARALLEL
        const [classifiedGenres, classifiedHardNos, classifiedAudience] = await Promise.all([
            classifyGenres(agentInfo.genres_raw),
            classifyHardNos(agentInfo.hard_nos_raw),
            classifyAudience(agentInfo.audience_raw, agentInfo.genres_raw)
        ]);

        // Map to boolean fields
        const genreBooleans = genresToBooleans(classifiedGenres);

        // Merge everything into final result
        const result = {
            agent_name: agentInfo.agent_name || 'Unknown',
            agent_name_evidence: agentInfo.agent_name_evidence || 'Not found',
            agency_name: agentInfo.agency_name || 'Unknown',
            agency_name_evidence: agentInfo.agency_name_evidence || 'Not found',
            agent_role: agentInfo.agent_role || 'Unknown',
            contact_email: agentInfo.contact_email || '',
            email: agentInfo.contact_email || '',
            submission_url: agentInfo.submission_url || '',
            is_open_to_submissions: agentInfo.is_open_to_submissions || false,
            is_open_to_submissions_evidence: agentInfo.is_open_to_submissions_evidence || 'Not found',
            status_notice: agentInfo.status_notice || '',
            estimated_response_time: agentInfo.estimated_response_time || '',
            accepted_genres_fiction: classifiedGenres.fiction || [],
            accepted_genres_nonfiction: classifiedGenres.nonfiction || [],
            genres_raw: agentInfo.genres_raw || '',
            hard_nos: classifiedHardNos,
            hard_nos_raw: agentInfo.hard_nos_raw || '',
            audience: classifiedAudience,
            audience_raw: agentInfo.audience_raw || '',
            manuscript_wishlist_summary: agentInfo.manuscript_wishlist_summary || '',
            target_audience: agentInfo.target_audience || '',
            specific_keywords: agentInfo.specific_keywords || [],
            requires_bio: agentInfo.requires_bio || false,
            requires_expose: agentInfo.requires_expose || false,
            requires_manuscript: agentInfo.requires_manuscript || false,
            ...genreBooleans
        };

        // Merge with known fields
        if (knownFields) {
            Object.entries(knownFields).forEach(([key, value]) => {
                if (value && value !== 'Unknown' && value !== '') {
                    result[key] = value;
                }
            });
        }

        console.log(`\n2-Phase extraction complete for: ${result.agent_name}`);
        console.log(`   Genres: ${[...classifiedGenres.fiction, ...classifiedGenres.nonfiction].join(', ') || 'none'}`);
        console.log(`   Hard nos: ${classifiedHardNos.join(', ') || 'none'}`);
        console.log(`   Audience: ${classifiedAudience.join(', ') || 'none'}`);

        return result;

    } catch (error) {
        console.error('Extraction error:', error.message);

        const errorGenres = {};
        const tempBooleans = genresToBooleans({ fiction: [], nonfiction: [] });
        Object.keys(tempBooleans).forEach(key => { errorGenres[key] = false; });

        return {
            agent_name: 'Error',
            agency_name: 'Error',
            country: 'Unknown',
            website: '',
            email: '',
            is_open_to_submissions: false,
            requires_bio: false,
            requires_expose: false,
            requires_manuscript: false,
            audience: [],
            ...errorGenres,
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

/**
 * Triage: Identify which pages contain agent info from snippets
 * 1 LLM call for all pages instead of 25 individual calls
 */
export async function triagePages(pageSnippets, baseUrl) {
    try {
        if (!pageSnippets || pageSnippets.length === 0) {
            return [];
        }

        if (pageSnippets.length <= 2) {
            return pageSnippets.map((_, i) => i);
        }

        console.log(`\nTriage: Analyzing ${pageSnippets.length} page snippets...`);

        const snippetList = pageSnippets.map((s, i) =>
            `[${i}] URL: ${s.url}\n    Title: ${s.title}\n    Preview: ${s.preview}`
        ).join('\n\n');

        const prompt = `You are analyzing pages from ${baseUrl} to find literary agent profile pages.

Pages to analyze:
${snippetList}

Which pages contain individual literary agent information (agent name, genres they represent, submission guidelines, contact info)?

Output ONLY a JSON array of page indices that contain agent info:
{"relevant": [0, 3, 7]}

Rules:
- Only include pages that clearly contain agent/person profile information
- Skip general pages (about us, blog, news, legal, events)
- Skip pages that are just lists/directories without detailed agent info
- START with { and END with }`;

        const response = await axios.post(`${OLLAMA_URL}/api/generate`, {
            model: MODEL,
            prompt: prompt,
            stream: false,
            options: {
                temperature: 0.0,
                num_predict: 500,
                top_p: 0.1,
                num_ctx: 4096
            },
            keep_alive: 0
        }, {
            timeout: 30000
        });

        const result = response.data.response;
        const jsonMatch = result.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            console.log(`   Triage: Failed to parse, using all pages`);
            return pageSnippets.map((_, i) => i);
        }

        const parsed = JSON.parse(jsonMatch[0]);
        const relevant = parsed.relevant || [];

        console.log(`   Triage: ${relevant.length}/${pageSnippets.length} pages are relevant`);
        relevant.forEach(i => {
            if (pageSnippets[i]) {
                console.log(`      [${i}] ${pageSnippets[i].url}`);
            }
        });

        return relevant;

    } catch (error) {
        console.log(`   Triage failed: ${error.message}, using all pages`);
        return pageSnippets.map((_, i) => i);
    }
}

/**
 * Prioritize URLs using LLM to identify agent-relevant pages
 */
export async function prioritizeUrlsWithLLM(urls, baseUrl) {
    try {
        if (!urls || urls.length === 0) {
            return [];
        }

        if (urls.length <= 3) {
            return urls;
        }

        console.log(`\nUsing LLM to prioritize ${urls.length} URLs...`);

        const prompt = `You are analyzing URLs from a literary agency website: ${baseUrl}

Your task: Rank these URLs by likelihood of containing literary agent information (agent names, contact info, genres they represent, submission guidelines).

URLs to analyze:
${urls.map((url, i) => `${i + 1}. ${url}`).join('\n')}

Output ONLY a JSON array with this format:
[
  {"url": "exact_url_from_list", "score": 5},
  {"url": "exact_url_from_list", "score": 4}
]

Scoring: 5=agent pages, 4=likely agent, 3=maybe, 2=unlikely, 1=irrelevant

CRITICAL: Output ONLY the JSON array. START with [ and END with ]`;

        const response = await axios.post(`${OLLAMA_URL}/api/generate`, {
            model: MODEL,
            prompt: prompt,
            stream: false,
            options: {
                temperature: 0.0,
                num_predict: 2000,
                top_p: 0.1,
                num_ctx: 4096
            }
        }, {
            timeout: 30000
        });

        const rawResponse = response.data.response;

        let rankings = [];
        try {
            const jsonMatch = rawResponse.match(/\[[\s\S]*\]/);
            if (jsonMatch) {
                rankings = JSON.parse(jsonMatch[0]);
            } else {
                return urls;
            }
        } catch (parseError) {
            return urls;
        }

        rankings.sort((a, b) => b.score - a.score);
        const prioritizedUrls = rankings.map(r => r.url);
        const missingUrls = urls.filter(url => !prioritizedUrls.includes(url));
        const finalUrls = [...prioritizedUrls, ...missingUrls];

        console.log(`   Prioritized URLs (top 5):`);
        finalUrls.slice(0, 5).forEach((url, i) => {
            const ranking = rankings.find(r => r.url === url);
            console.log(`      ${i + 1}. [Score ${ranking?.score || '?'}] ${url}`);
        });

        return finalUrls;

    } catch (error) {
        console.log(`   LLM prioritization failed: ${error.message}`);
        return urls;
    }
}
