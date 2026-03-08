/**
 * Data validation and quality assurance functions
 */

/**
 * Validate email address
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
export function isValidEmail(email) {
    if (!email || typeof email !== 'string') return false;

    // Basic email regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) return false;

    // Blacklist generic emails (not personal agent emails)
    const genericPrefixes = [
        'info@',
        'kontakt@',
        'contact@',
        'office@',
        'admin@',
        'hello@',
        'mail@',
        'support@',
        'service@'
    ];

    const lowerEmail = email.toLowerCase();
    if (genericPrefixes.some(prefix => lowerEmail.startsWith(prefix))) {
        return false;
    }

    return true;
}

/**
 * Validate URL
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid
 */
export function isValidUrl(url) {
    if (!url || typeof url !== 'string') return false;

    try {
        const urlObj = new URL(url);
        return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
    } catch {
        return false;
    }
}

/**
 * Normalize agent name
 * @param {string} name - Name to normalize
 * @returns {string} Normalized name
 */
export function normalizeName(name) {
    if (!name || typeof name !== 'string') return '';

    // Trim whitespace
    let normalized = name.trim();

    // Handle "Last, First" format -> "First Last"
    if (normalized.includes(',')) {
        const parts = normalized.split(',').map(p => p.trim());
        if (parts.length === 2) {
            normalized = `${parts[1]} ${parts[0]}`;
        }
    }

    // Remove extra whitespace
    normalized = normalized.replace(/\s+/g, ' ');

    return normalized;
}

/**
 * Check if two agents are duplicates
 * @param {Object} agent1 - First agent
 * @param {Object} agent2 - Second agent
 * @returns {boolean} True if duplicate
 */
export function isDuplicate(agent1, agent2) {
    // Normalize names for comparison
    const name1 = normalizeName(agent1.agent_name || '').toLowerCase();
    const name2 = normalizeName(agent2.agent_name || '').toLowerCase();

    // Check name match
    if (name1 && name2 && name1 === name2) {
        return true;
    }

    // Check email match (if both have emails)
    const email1 = (agent1.email || '').toLowerCase().trim();
    const email2 = (agent2.email || '').toLowerCase().trim();
    if (email1 && email2 && email1 === email2) {
        return true;
    }

    // Check if names are very similar (fuzzy match)
    // Simple approach: if one name contains the other
    if (name1 && name2) {
        if (name1.includes(name2) || name2.includes(name1)) {
            // Also check if they're from the same agency
            const agency1 = (agent1.agency_name || '').toLowerCase();
            const agency2 = (agent2.agency_name || '').toLowerCase();
            if (agency1 && agency2 && agency1 === agency2) {
                return true;
            }
        }
    }

    return false;
}

/**
 * Remove duplicates from agents array
 * @param {Array} agents - Array of agents
 * @returns {Array} Deduplicated array
 */
export function removeDuplicates(agents) {
    const unique = [];

    for (const agent of agents) {
        const isDupe = unique.some(existing => isDuplicate(existing, agent));
        if (!isDupe) {
            unique.push(agent);
        } else {
            console.log(`🔄 Duplicate removed: ${agent.agent_name}`);
        }
    }

    return unique;
}

/**
 * Calculate confidence score for an agent (0-100)
 * @param {Object} agent - Agent data
 * @returns {number} Confidence score
 */
export function calculateConfidence(agent) {
    let score = 0;

    // Agent name (required) - 30 points (increased: most important!)
    if (agent.agent_name && agent.agent_name !== 'Unknown' && agent.agent_name !== 'Error') {
        score += 30;
    }

    // Valid email - 20 points
    if (isValidEmail(agent.email)) {
        score += 20;
    }

    // Agency name - 20 points (increased: very important!)
    if (agent.agency_name && agent.agency_name !== 'Unknown') {
        score += 20;
    }

    // At least one genre selected - 5 points (decreased: nice to have, not critical!)
    // Support both old (boolean) and new (array) genre schemas
    const genreFields = Object.keys(agent).filter(key => key.startsWith('genre_'));
    const hasOldGenre = genreFields.some(field => agent[field] === true);
    const hasNewGenre = (
        (Array.isArray(agent.accepted_genres_fiction) && agent.accepted_genres_fiction.length > 0) ||
        (Array.isArray(agent.accepted_genres_nonfiction) && agent.accepted_genres_nonfiction.length > 0)
    );
    if (hasOldGenre || hasNewGenre) {
        score += 5;
    }

    // Submission status known - 10 points
    if (typeof agent.is_open_to_submissions === 'boolean') {
        score += 10;
    }

    // At least one requirement specified - 10 points
    if (agent.requires_bio || agent.requires_expose || agent.requires_project_plan) {
        score += 10;
    }

    // Valid website - 5 points
    if (isValidUrl(agent.website)) {
        score += 5;
    }

    // Total possible: 30+20+20+5+10+10+5 = 100 points
    return Math.min(score, 100);
}

/**
 * Validate and clean agent data
 * @param {Object} agent - Raw agent data
 * @returns {Object} Cleaned agent data with validation metadata
 */
export function validateAgent(agent) {
    const cleaned = { ...agent };

    // Normalize name
    if (cleaned.agent_name) {
        cleaned.agent_name = normalizeName(cleaned.agent_name);
    }

    // Convert "Unknown" to empty string or empty array
    Object.keys(cleaned).forEach(key => {
        if (cleaned[key] === 'Unknown') {
            // For array fields, use empty array; for others, empty string
            if (key.includes('genres') || key.includes('keywords') || key.includes('hard_nos')) {
                cleaned[key] = [];
            } else {
                cleaned[key] = '';
            }
        }
        // Trim strings (but not arrays!)
        if (typeof cleaned[key] === 'string') {
            cleaned[key] = cleaned[key].trim();
        }
        // Ensure arrays are actually arrays
        if (key.includes('genres') || key.includes('keywords') || key.includes('hard_nos') || key.includes('_evidence')) {
            if (!Array.isArray(cleaned[key])) {
                cleaned[key] = [];
            }
        }
    });

    // Validate email
    if (cleaned.email && !isValidEmail(cleaned.email)) {
        console.log(`⚠️  Invalid email removed: ${cleaned.email}`);
        cleaned.email = '';
    }

    // Validate URLs
    if (cleaned.website && !isValidUrl(cleaned.website)) {
        console.log(`⚠️  Invalid website removed: ${cleaned.website}`);
        cleaned.website = '';
    }

    // Calculate confidence score
    cleaned.confidence_score = calculateConfidence(cleaned);

    // Add validation metadata
    cleaned.is_valid = cleaned.agent_name && cleaned.agent_name !== 'Error' && cleaned.confidence_score >= 40;

    return cleaned;
}

/**
 * Check if agent meets minimum quality standards
 * @param {Object} agent - Agent data
 * @returns {boolean} True if meets standards
 */
export function meetsQualityStandards(agent) {
    // Must have name
    if (!agent.agent_name || agent.agent_name === 'Unknown' || agent.agent_name === 'Error') {
        return false;
    }

    // Must have either email OR website OR agency
    if (!agent.email && !agent.website && !agent.agency_name) {
        return false;
    }

    // Confidence score must be at least 20% (lowered for debugging)
    if (agent.confidence_score < 20) {
        console.log(`⚠️ Rejected: ${agent.agent_name} - confidence too low (${agent.confidence_score}%)`);
        return false;
    }

    console.log(`✅ Accepted: ${agent.agent_name} - confidence ${agent.confidence_score}%`);
    return true;
}
