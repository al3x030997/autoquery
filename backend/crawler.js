import { scrapeUrl } from './scraper.js';
import { extractWithOllama, triagePages } from './ollama.js';
import { validateAgent, removeDuplicates, meetsQualityStandards } from './validator.js';
import { extractCountry } from './impressum.js';
import { prioritizeUrlsWithLLM } from './ollama.js';
import axios from 'axios';
import * as cheerio from 'cheerio';

// Maximum number of agent pages to crawl before asking user confirmation
const MAX_AGENT_LINKS = 25;
// Maximum concurrent HTTP requests for scraping
const SCRAPE_CONCURRENCY = 5;

/**
 * Extract agency-wide fields that are shared across all agents
 */
function extractAgencyWideFields(agent) {
    return {
        agency_name: agent.agency_name,
        agency_name_evidence: agent.agency_name_evidence,
        country: agent.country,
    };
}

/**
 * Check if we have confident agency-wide knowledge
 */
function hasConfidentAgencyInfo(knowledgeBase) {
    return knowledgeBase &&
           knowledgeBase.agency_name &&
           knowledgeBase.agency_name !== 'Unknown' &&
           knowledgeBase.agency_name !== '';
}

/**
 * Scrape multiple URLs in parallel with concurrency limit
 * @param {Array<string>} urls - URLs to scrape
 * @param {number} concurrency - Max concurrent requests
 * @returns {Promise<Array>} Array of {url, content, error} objects
 */
async function scrapeParallel(urls, concurrency = SCRAPE_CONCURRENCY) {
    const results = [];
    const queue = [...urls];

    async function worker() {
        while (queue.length > 0) {
            const url = queue.shift();
            try {
                const content = await scrapeUrl(url);
                results.push({ url, content, error: null });
                console.log(`   ✅ Scraped: ${url} (${content.text.length} chars)`);
            } catch (error) {
                results.push({ url, content: null, error: error.message });
                console.log(`   ❌ Failed: ${url} (${error.message})`);
            }
        }
    }

    // Launch workers up to concurrency limit
    const workers = [];
    for (let i = 0; i < Math.min(concurrency, urls.length); i++) {
        workers.push(worker());
    }
    await Promise.all(workers);

    return results;
}

/**
 * Parse sitemap.xml and extract all URLs
 */
async function parseSitemap(baseUrl) {
    try {
        const urlObj = new URL(baseUrl);
        const baseOrigin = `${urlObj.protocol}//${urlObj.hostname}`;

        const sitemapUrls = [
            `${baseOrigin}/sitemap.xml`,
            `${baseOrigin}/sitemap_index.xml`,
            `${baseOrigin}/sitemap-index.xml`,
            `${baseOrigin}/sitemap1.xml`
        ];

        for (const sitemapUrl of sitemapUrls) {
            try {
                console.log(`📍 Trying sitemap: ${sitemapUrl}`);
                const response = await axios.get(sitemapUrl, {
                    timeout: 5000,
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    }
                });

                const $ = cheerio.load(response.data, { xmlMode: true });
                const urls = [];

                $('url > loc').each((i, elem) => {
                    const url = $(elem).text().trim();
                    if (url) urls.push(url);
                });

                // Handle sitemap index
                const sitemapLinks = [];
                $('sitemap > loc').each((i, elem) => {
                    const url = $(elem).text().trim();
                    if (url) sitemapLinks.push(url);
                });

                if (sitemapLinks.length > 0) {
                    console.log(`📚 Found sitemap index with ${sitemapLinks.length} sitemaps`);
                    for (const link of sitemapLinks.slice(0, 5)) {
                        try {
                            const subResponse = await axios.get(link, {
                                timeout: 5000,
                                headers: {
                                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                                }
                            });
                            const $sub = cheerio.load(subResponse.data, { xmlMode: true });
                            $sub('url > loc').each((i, elem) => {
                                const url = $sub(elem).text().trim();
                                if (url) urls.push(url);
                            });
                        } catch (err) {
                            console.log(`⚠️  Failed to fetch sub-sitemap: ${link}`);
                        }
                    }
                }

                if (urls.length > 0) {
                    console.log(`✅ Found ${urls.length} URLs in sitemap`);
                    return urls;
                }
            } catch (err) {
                continue;
            }
        }

        return null;
    } catch (error) {
        console.log(`⚠️  Sitemap parsing failed: ${error.message}`);
        return null;
    }
}

/**
 * Filter links for crawling with LLM-based prioritization
 */
async function filterAgentLinks(links, baseUrl) {
    const cleaned = links.filter(link => {
        if (link.match(/\.(pdf|jpg|png|gif|doc|docx|xml|txt|css|js|json|svg|ico)$/i)) {
            return false;
        }
        if (link.match(/\/(impressum|datenschutz|privacy|legal|agb|terms|cookie|disclaimer|haftung)/i)) {
            return false;
        }
        return true;
    });

    const uniqueLinks = [...new Set(cleaned)];
    console.log(`  📋 After technical filtering: ${uniqueLinks.length} URLs`);

    const prioritized = await prioritizeUrlsWithLLM(uniqueLinks, baseUrl);
    return prioritized.slice(0, MAX_AGENT_LINKS);
}

/**
 * Crawl a URL and extract all agents using 2-phase approach:
 *
 * Step 1: Discover & scrape pages (parallel HTTP)
 * Step 2: Triage — 1 LLM call to identify relevant pages from snippets
 * Step 3: Extract — only relevant pages get full 2-phase LLM extraction
 */
export async function crawlForAgents(url, options = {}) {
    const agents = [];
    let agencyKnowledge = null;
    const { singleUrlMode = false } = options;

    try {
        // Normalize URL
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
            console.log(`🔧 Auto-corrected URL to: ${url}`);
        }

        console.log(`\n🕷️  Starting crawl from: ${url}`);
        if (singleUrlMode) {
            console.log(`🎯 Single URL Mode: Only crawling this exact URL`);
        }

        let agentLinks = [];
        let allLinks = [];
        let country = 'Unknown';

        if (singleUrlMode) {
            console.log(`📄 Direct crawl mode - no link discovery`);
            agentLinks = [];
            allLinks = [];
        } else {
            // Step 1: Get URLs from sitemap or page
            console.log(`\n📡 Attempting to parse sitemap.xml...`);
            const sitemapUrls = await parseSitemap(url);

            if (sitemapUrls && sitemapUrls.length > 0) {
                console.log(`✅ Using sitemap with ${sitemapUrls.length} URLs`);
                agentLinks = await filterAgentLinks(sitemapUrls, url);
                allLinks = sitemapUrls;
            } else {
                console.log(`⚠️  No sitemap found, falling back to page scraping`);
                const mainPage = await scrapeUrl(url);
                console.log(`📄 Found ${mainPage.links.length} total links from page`);
                agentLinks = await filterAgentLinks(mainPage.links, url);
                allLinks = mainPage.links;
            }

            console.log(`🎯 Filtered to ${agentLinks.length} potential agent pages`);

            // Safety check
            if (agentLinks.length > MAX_AGENT_LINKS) {
                const estimatedTime = Math.round((agentLinks.length * 3) / 60);
                return {
                    warning: true,
                    tooManyLinks: true,
                    message: `Found ${agentLinks.length} potential agent pages (limit: ${MAX_AGENT_LINKS})`,
                    foundLinks: agentLinks.length,
                    limit: MAX_AGENT_LINKS,
                    estimatedTime: estimatedTime,
                    sampleUrls: agentLinks.slice(0, 10)
                };
            }

            // Extract country from impressum (parallel with scraping)
            console.log(`\n🌍 Extracting country information...`);
            country = await extractCountry(url, allLinks);
        }

        // ========================================
        // STEP 1: Scrape all pages in parallel
        // ========================================
        const allUrls = [url, ...agentLinks.filter(l => l !== url)];
        const uniqueUrls = [...new Set(allUrls)];

        console.log(`\n📥 Step 1: Scraping ${uniqueUrls.length} pages in parallel...`);
        const scrapedPages = await scrapeParallel(uniqueUrls);
        const successfulPages = scrapedPages.filter(p => p.content && p.content.text.length > 200);
        console.log(`✅ Successfully scraped ${successfulPages.length}/${uniqueUrls.length} pages`);

        // ========================================
        // STEP 2: Triage — 1 LLM call for all pages
        // ========================================
        let pagesToExtract = successfulPages;

        if (successfulPages.length > 2 && !singleUrlMode) {
            console.log(`\n🔍 Step 2: Triage — identifying relevant pages...`);
            const snippets = successfulPages.map(p => ({
                url: p.url,
                title: p.content.title || '',
                preview: p.content.text.substring(0, 300)
            }));

            const relevantIndices = await triagePages(snippets, url);
            pagesToExtract = relevantIndices
                .filter(i => i >= 0 && i < successfulPages.length)
                .map(i => successfulPages[i]);

            console.log(`✅ Triage: ${pagesToExtract.length} pages selected for extraction`);
        }

        // ========================================
        // STEP 3: Extract agent data from relevant pages
        // ========================================
        console.log(`\n🤖 Step 3: Extracting agent data from ${pagesToExtract.length} pages...`);

        for (const page of pagesToExtract) {
            try {
                console.log(`\n🔍 Extracting: ${page.url}`);

                const knownFields = hasConfidentAgencyInfo(agencyKnowledge) ? agencyKnowledge : null;
                const agentData = await extractWithOllama(page.content, 0.0, knownFields);

                // Add country
                if (country && country !== 'Unknown') {
                    agentData.country = country;
                } else if (agencyKnowledge && agencyKnowledge.country) {
                    agentData.country = agencyKnowledge.country;
                }

                // Validate
                const validatedAgent = validateAgent(agentData);

                // Build agency knowledge from first successful extraction
                if (!agencyKnowledge && validatedAgent && validatedAgent.agency_name) {
                    agencyKnowledge = extractAgencyWideFields(validatedAgent);
                    console.log(`📚 Agency knowledge established: ${agencyKnowledge.agency_name}`);
                }

                // Only add if quality standards met
                if (meetsQualityStandards(validatedAgent)) {
                    agents.push({
                        ...validatedAgent,
                        source_url: page.url,
                        source_title: page.content.title,
                        source_snippet: page.content.textSnippet,
                        suggestions: {
                            emails: page.content.allEmails || [],
                            websites: page.content.allUrls || []
                        }
                    });
                    console.log(`✅ Found agent: ${validatedAgent.agent_name} (confidence: ${validatedAgent.confidence_score}%)`);
                } else {
                    console.log(`⚠️  Agent didn't meet quality standards`);
                }

            } catch (error) {
                console.error(`❌ Error extracting ${page.url}: ${error.message}`);
            }
        }

        // Step 4: Remove duplicates
        console.log(`\n🔄 Removing duplicates...`);
        const uniqueAgents = removeDuplicates(agents);
        console.log(`📊 Before: ${agents.length} → After: ${uniqueAgents.length} agents`);

        console.log(`\n✅ Crawl complete! Found ${uniqueAgents.length} unique agents`);
        return uniqueAgents;

    } catch (error) {
        console.error(`❌ Crawl error: ${error.message}`);
        throw error;
    }
}
