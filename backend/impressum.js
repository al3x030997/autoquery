import { scrapeUrl } from './scraper.js';

/**
 * Find impressum/legal/contact page URL
 * @param {Array} links - All links from the website
 * @param {string} baseUrl - Base URL
 * @returns {string|null} Impressum page URL
 */
function findImpressumUrl(links, baseUrl) {
    const impressumPatterns = [
        /\/impressum\/?$/i,
        /\/imprint\/?$/i,
        /\/legal\/?$/i,
        /\/legal-notice\/?$/i,
        /\/contact\/?$/i,
        /\/about\/?$/i,
        /\/kontakt\/?$/i
    ];

    // Find matching links
    for (const pattern of impressumPatterns) {
        const match = links.find(link => pattern.test(link));
        if (match) {
            return match;
        }
    }

    return null;
}

/**
 * Extract country from text content
 * @param {string} text - Text content to search
 * @returns {string|null} Country name or null
 */
function extractCountryFromText(text) {
    if (!text) return null;

    const lowerText = text.toLowerCase();

    // Country patterns with variations
    const countryPatterns = [
        // Germany
        { pattern: /\b(deutschland|germany)\b/i, country: 'Germany' },
        // Austria
        { pattern: /\b(österreich|austria|oesterreich)\b/i, country: 'Austria' },
        // Switzerland
        { pattern: /\b(schweiz|switzerland|suisse|svizzera)\b/i, country: 'Switzerland' },
        // United States
        { pattern: /\b(united states|usa|u\.s\.a\.|america)\b/i, country: 'United States' },
        // United Kingdom
        { pattern: /\b(united kingdom|uk|u\.k\.|great britain|england|scotland|wales)\b/i, country: 'United Kingdom' },
        // Canada
        { pattern: /\b(canada|kanada)\b/i, country: 'Canada' },
        // Australia
        { pattern: /\b(australia|australien)\b/i, country: 'Australia' },
        // New Zealand
        { pattern: /\b(new zealand|neuseeland)\b/i, country: 'New Zealand' },
        // Ireland
        { pattern: /\b(ireland|irland)\b/i, country: 'Ireland' },
        // France
        { pattern: /\b(france|frankreich)\b/i, country: 'France' },
        // Spain
        { pattern: /\b(spain|spanien|españa)\b/i, country: 'Spain' },
        // Italy
        { pattern: /\b(italy|italien|italia)\b/i, country: 'Italy' },
        // Netherlands
        { pattern: /\b(netherlands|niederlande|holland)\b/i, country: 'Netherlands' },
        // Belgium
        { pattern: /\b(belgium|belgien|belgique)\b/i, country: 'Belgium' }
    ];

    // Try to find explicit country mention
    for (const { pattern, country } of countryPatterns) {
        if (pattern.test(lowerText)) {
            return country;
        }
    }

    // German postal code patterns (more specific)
    // Germany: 10000-99999 (5 digits)
    const germanZipMatch = text.match(/\b([1-9]\d{4})\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\b/);
    if (germanZipMatch) {
        const zip = parseInt(germanZipMatch[1]);
        if (zip >= 10000 && zip <= 99999) {
            return 'Germany';
        }
    }

    // Austrian postal code: 1000-9999 (4 digits) + Austrian city names
    const austrianCities = ['wien', 'vienna', 'salzburg', 'innsbruck', 'graz', 'linz'];
    const austrianZipMatch = text.match(/\b([1-9]\d{3})\s+([A-ZÄÖÜ][a-zäöüß]+)\b/);
    if (austrianZipMatch) {
        const city = austrianZipMatch[2].toLowerCase();
        if (austrianCities.some(ac => city.includes(ac))) {
            return 'Austria';
        }
    }

    // Swiss postal code: 1000-9999 (4 digits) + Swiss city names
    const swissCities = ['zürich', 'zurich', 'bern', 'geneva', 'genf', 'basel', 'lausanne'];
    const swissZipMatch = text.match(/\b([1-9]\d{3})\s+([A-ZÄÖÜ][a-zäöüß]+)\b/);
    if (swissZipMatch) {
        const city = swissZipMatch[2].toLowerCase();
        if (swissCities.some(sc => city.includes(sc))) {
            return 'Switzerland';
        }
    }

    // US ZIP code: 5 digits or 5+4 format + US state names
    const usStates = [
        'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut',
        'delaware', 'florida', 'georgia', 'hawaii', 'idaho', 'illinois', 'indiana', 'iowa',
        'kansas', 'kentucky', 'louisiana', 'maine', 'maryland', 'massachusetts', 'michigan',
        'minnesota', 'mississippi', 'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire',
        'new jersey', 'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
        'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
        'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington', 'west virginia',
        'wisconsin', 'wyoming', 'ny', 'ca', 'tx', 'fl', 'il', 'pa', 'oh', 'ga', 'nc', 'mi'
    ];
    if (usStates.some(state => lowerText.includes(state))) {
        return 'United States';
    }

    // UK postcode pattern
    const ukPostcodeMatch = text.match(/\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b/);
    if (ukPostcodeMatch) {
        return 'United Kingdom';
    }

    return null;
}

/**
 * Extract country from domain TLD (fallback)
 * @param {string} url - Website URL
 * @returns {string|null} Country name or null
 */
function extractCountryFromDomain(url) {
    try {
        const urlObj = new URL(url);
        const hostname = urlObj.hostname.toLowerCase();

        const tldMap = {
            '.de': 'Germany',
            '.at': 'Austria',
            '.ch': 'Switzerland',
            '.com': null, // Too generic
            '.co.uk': 'United Kingdom',
            '.uk': 'United Kingdom',
            '.us': 'United States',
            '.ca': 'Canada',
            '.au': 'Australia',
            '.nz': 'New Zealand',
            '.ie': 'Ireland',
            '.fr': 'France',
            '.es': 'Spain',
            '.it': 'Italy',
            '.nl': 'Netherlands',
            '.be': 'Belgium'
        };

        // Check for country-specific TLDs
        for (const [tld, country] of Object.entries(tldMap)) {
            if (hostname.endsWith(tld)) {
                return country;
            }
        }

        return null;
    } catch {
        return null;
    }
}

/**
 * Parse impressum/legal page to extract country
 * @param {string} url - Base URL of the website
 * @param {Array} links - All links from the main page
 * @returns {Promise<string|null>} Country name or null
 */
export async function extractCountry(url, links) {
    try {
        // Strategy 1: Find and parse impressum/legal page
        const impressumUrl = findImpressumUrl(links, url);

        if (impressumUrl) {
            console.log(`📋 Found impressum/legal page: ${impressumUrl}`);
            try {
                const impressumPage = await scrapeUrl(impressumUrl);
                const country = extractCountryFromText(impressumPage.text);
                if (country) {
                    console.log(`✅ Country from impressum: ${country}`);
                    return country;
                }
            } catch (error) {
                console.log(`⚠️  Failed to scrape impressum: ${error.message}`);
            }
        }

        // Strategy 2: Check main page content
        console.log(`📋 Checking main page for country info...`);
        try {
            const mainPage = await scrapeUrl(url);
            const country = extractCountryFromText(mainPage.text);
            if (country) {
                console.log(`✅ Country from main page: ${country}`);
                return country;
            }
        } catch (error) {
            console.log(`⚠️  Failed to check main page: ${error.message}`);
        }

        // Strategy 3: Fallback to domain TLD
        console.log(`📋 Falling back to domain TLD...`);
        const countryFromDomain = extractCountryFromDomain(url);
        if (countryFromDomain) {
            console.log(`✅ Country from domain: ${countryFromDomain}`);
            return countryFromDomain;
        }

        console.log(`⚠️  Could not determine country`);
        return null;

    } catch (error) {
        console.error(`❌ Error extracting country: ${error.message}`);
        return null;
    }
}
