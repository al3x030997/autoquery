import { extractWithOllama } from './ollama.js';

/**
 * Extract agent data multiple times with different temperatures for self-consistency check
 * @param {Object} content - Content to extract from
 * @param {number} samples - Number of samples to generate (default: 2)
 * @param {Object} knownFields - Already known fields from previous pages (optional)
 * @returns {Promise<Array>} Array of extraction results
 */
async function extractMultipleSamples(content, samples = 2, knownFields = null) {
    const temperatures = [0.0, 0.3]; // Different temperatures for diversity (reduced from 3 to 2 to save costs)
    const results = [];

    console.log(`🔄 Running self-consistency check with ${samples} samples...`);

    for (let i = 0; i < samples; i++) {
        try {
            const result = await extractWithOllama(content, temperatures[i] || 0.0, knownFields);
            results.push(result);
            console.log(`   Sample ${i + 1}/${samples} completed (temp: ${temperatures[i] || 0.0})`);
        } catch (error) {
            console.error(`   ⚠️  Sample ${i + 1} failed: ${error.message}`);
            // Continue with remaining samples
        }
    }

    return results;
}

/**
 * Calculate consistency score for a specific field across multiple results
 * @param {Array} results - Array of extraction results
 * @param {string} field - Field name to check
 * @returns {Object} Consistency info { score: 0-1, mostCommon: value, count: number }
 */
function calculateFieldConsistency(results, field) {
    const values = results.map(r => {
        const value = r[field];

        // Normalize for comparison
        if (typeof value === 'string') {
            return value.toLowerCase().trim();
        }
        if (typeof value === 'boolean') {
            return value.toString();
        }
        return value;
    });

    // Count occurrences
    const counts = {};
    values.forEach(val => {
        const key = String(val);
        counts[key] = (counts[key] || 0) + 1;
    });

    // Find most common value
    let mostCommon = null;
    let maxCount = 0;

    for (const [value, count] of Object.entries(counts)) {
        if (count > maxCount) {
            maxCount = count;
            mostCommon = value;
        }
    }

    // Consistency score: percentage of results that agree
    const score = maxCount / results.length;

    return {
        score,
        mostCommon: mostCommon === 'null' || mostCommon === 'undefined' ? null : mostCommon,
        count: maxCount,
        total: results.length,
        allValues: values
    };
}

/**
 * Calculate overall consistency across all fields
 * @param {Array} results - Array of extraction results
 * @returns {Object} Overall consistency analysis
 */
function calculateOverallConsistency(results) {
    if (results.length === 0) {
        return { score: 0, fieldAnalysis: {}, needsReview: true };
    }

    const allFields = Object.keys(results[0]);
    const fieldAnalysis = {};
    let totalScore = 0;
    let criticalFieldsInconsistent = [];

    // Critical fields that must be consistent
    const criticalFields = ['agent_name', 'email', 'agency_name'];

    for (const field of allFields) {
        // Skip metadata fields
        if (field === 'source_url' || field === 'timestamp' || field === 'error') {
            continue;
        }

        const consistency = calculateFieldConsistency(results, field);
        fieldAnalysis[field] = consistency;
        totalScore += consistency.score;

        // Check if critical field is inconsistent
        if (criticalFields.includes(field) && consistency.score < 0.67) {
            criticalFieldsInconsistent.push(field);
        }
    }

    const avgScore = totalScore / Object.keys(fieldAnalysis).length;

    return {
        score: avgScore,
        fieldAnalysis,
        criticalFieldsInconsistent,
        needsReview: avgScore < 0.7 || criticalFieldsInconsistent.length > 0
    };
}

/**
 * Merge multiple extraction results using majority voting
 * @param {Array} results - Array of extraction results
 * @returns {Object} Merged result with most common values
 */
function mergeResultsByVoting(results) {
    if (results.length === 0) {
        return null;
    }

    if (results.length === 1) {
        return results[0];
    }

    const merged = {};
    const allFields = Object.keys(results[0]);

    for (const field of allFields) {
        const consistency = calculateFieldConsistency(results, field);

        // Use the most common value
        let value = consistency.mostCommon;

        // Convert back from string to original type
        if (value === 'true') value = true;
        if (value === 'false') value = false;
        if (value === 'null') value = null;

        // For string fields, restore original case
        if (field === 'agent_name' || field === 'agency_name' || field === 'email' || field === 'country') {
            // Find the original value with proper casing
            const original = results.find(r => {
                const val = r[field];
                return typeof val === 'string' && val.toLowerCase().trim() === value;
            });
            if (original && original[field]) {
                value = original[field];
            }
        }

        merged[field] = value;
    }

    return merged;
}

/**
 * Extract with self-consistency check
 * @param {Object} content - Content to extract from
 * @param {number} samples - Number of samples (default: 2)
 * @param {Object} knownFields - Already known fields from previous pages (optional)
 * @returns {Promise<Object>} Extraction result with consistency metadata
 */
export async function extractWithSelfConsistency(content, samples = 2, knownFields = null) {
    try {
        // Extract multiple times
        const results = await extractMultipleSamples(content, samples, knownFields);

        if (results.length === 0) {
            throw new Error('All extraction attempts failed');
        }

        // Calculate consistency
        const consistency = calculateOverallConsistency(results);

        // Merge results using majority voting
        const mergedResult = mergeResultsByVoting(results);

        // Add consistency metadata
        mergedResult.self_consistency = {
            score: Math.round(consistency.score * 100), // 0-100
            samples: results.length,
            needsReview: consistency.needsReview,
            criticalFieldsInconsistent: consistency.criticalFieldsInconsistent,
            fieldScores: {}
        };

        // Add individual field consistency scores
        for (const [field, analysis] of Object.entries(consistency.fieldAnalysis)) {
            mergedResult.self_consistency.fieldScores[field] = {
                score: Math.round(analysis.score * 100),
                agreement: `${analysis.count}/${analysis.total}`
            };
        }

        // Log consistency summary
        console.log(`   ✅ Self-consistency score: ${mergedResult.self_consistency.score}%`);
        if (consistency.criticalFieldsInconsistent.length > 0) {
            console.log(`   ⚠️  Inconsistent critical fields: ${consistency.criticalFieldsInconsistent.join(', ')}`);
        }

        return mergedResult;

    } catch (error) {
        console.error(`❌ Self-consistency extraction failed: ${error.message}`);
        throw error;
    }
}

/**
 * Adjust confidence score based on self-consistency
 * @param {number} originalConfidence - Original confidence score (0-100)
 * @param {Object} selfConsistency - Self-consistency metadata
 * @returns {number} Adjusted confidence score
 */
export function adjustConfidenceWithConsistency(originalConfidence, selfConsistency) {
    if (!selfConsistency) return originalConfidence;

    const consistencyScore = selfConsistency.score;

    // High consistency (80%+) → boost confidence
    if (consistencyScore >= 80) {
        return Math.min(100, originalConfidence + 10);
    }

    // Medium consistency (60-80%) → slight boost
    if (consistencyScore >= 60) {
        return Math.min(100, originalConfidence + 5);
    }

    // Low consistency (<60%) → penalty
    if (consistencyScore < 60) {
        return Math.max(0, originalConfidence - 15);
    }

    return originalConfidence;
}
