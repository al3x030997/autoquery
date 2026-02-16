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

        // Remove script and style tags
        $('script, style, nav, footer, header').remove();

        // Extract title
        const title = $('title').text().trim() ||
                     $('h1').first().text().trim() ||
                     'No title found';

        // Extract main content
        // Try common content containers
        let text = '';
        const contentSelectors = [
            'article',
            'main',
            '.content',
            '.post-content',
            '.article-content',
            '#content',
            'body'
        ];

        for (const selector of contentSelectors) {
            const content = $(selector).first().text();
            if (content && content.length > 100) {
                text = content;
                break;
            }
        }

        // Fallback to body if no content found
        if (!text) {
            text = $('body').text();
        }

        // Clean up the text
        text = text
            .replace(/\s+/g, ' ')  // Replace multiple spaces with single space
            .replace(/\n+/g, '\n')  // Replace multiple newlines with single newline
            .trim();

        // Limit text length (to avoid overloading LLM)
        const maxLength = 8000;
        if (text.length > maxLength) {
            text = text.substring(0, maxLength) + '...';
        }

        return {
            title,
            text,
            wordCount: text.split(/\s+/).length
        };

    } catch (error) {
        throw new Error(`Failed to scrape URL: ${error.message}`);
    }
}
