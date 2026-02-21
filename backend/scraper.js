import axios from 'axios';
import * as cheerio from 'cheerio';

/**
 * Scrape content from a URL
 * @param {string} url - The URL to scrape
 * @returns {Promise<Object>} Scraped content with title and text
 */
export async function scrapeUrl(url) {
    try {
        // Fetch the page
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            },
            timeout: 10000 // 10 second timeout
        });

        const html = response.data;
        const $ = cheerio.load(html);

        // Remove script and style tags (keep header/nav/footer as they may contain important content)
        $('script, style').remove();

        // Extract title
        const title = $('title').text().trim() ||
                     $('h1').first().text().trim() ||
                     'No title found';

        // Extract main content — use body to capture everything including sidebars
        // Sidebars often contain genre tags, submission info, and other metadata
        // that would be missed by narrow selectors like 'article' or 'main'
        let text = $('body').text();

        // Clean up the text
        text = text
            .replace(/\s+/g, ' ')  // Replace multiple spaces with single space
            .replace(/\n+/g, '\n')  // Replace multiple newlines with single newline
            .trim();

        // Limit text length (to avoid overloading LLM)
        // Increased to 50000 to match LLM context window
        const maxLength = 50000;
        if (text.length > maxLength) {
            text = text.substring(0, maxLength) + '...';
        }

        // Extract all links from the page
        const links = [];
        $('a[href]').each((i, elem) => {
            const href = $(elem).attr('href');
            if (href) {
                try {
                    // Convert relative URLs to absolute
                    const absoluteUrl = new URL(href, url).href;
                    // Only include same-domain links
                    const baseUrl = new URL(url);
                    const linkUrl = new URL(absoluteUrl);
                    if (linkUrl.hostname === baseUrl.hostname) {
                        links.push(absoluteUrl);
                    }
                } catch (e) {
                    // Skip invalid URLs
                }
            }
        });

        // Keep original text snippet for preview (first 1500 chars)
        const textSnippet = text.substring(0, 1500);

        // Extract all emails for suggestions
        const emailRegex = /[\w.-]+@[\w.-]+\.\w+/g;
        const allEmails = [...new Set((text.match(emailRegex) || []).filter(email =>
            !email.includes('example.com') &&
            !email.includes('sentry.io') &&
            !email.includes('placeholder')
        ))];

        // Extract all URLs for suggestions
        const urlRegex = /https?:\/\/[^\s<>"]+/g;
        const allUrls = [...new Set((text.match(urlRegex) || []))];

        return {
            title,
            text,
            textSnippet,  // For Quick Preview in UI
            wordCount: text.split(/\s+/).length,
            links: [...new Set(links)], // Remove duplicates
            allEmails,  // For Field Suggestions
            allUrls     // For Field Suggestions
        };


    } catch (error) {
        throw new Error(`Failed to scrape URL: ${error.message}`);
    }
}
