"""
Versioned extraction prompts for Ollama-based agent profile extraction.
"""

PROMPT_VERSION = "1.0"

EXTRACTION_SYSTEM_PROMPT = """\
You are a data extraction specialist for literary agent profiles.
You extract structured information from agent profile web pages.
You ALWAYS respond with valid JSON only — no markdown, no commentary."""

EXTRACTION_USER_PROMPT = """\
Extract the following fields from this literary agent profile page text.
Respond with a single JSON object matching this exact schema:

{{
  "name": "Agent full name (required)",
  "agency": "Agency name or null",
  "genres": ["genre_one", "genre_two"],
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "audience": ["adult", "ya", "middle_grade", "children"],
  "hard_nos_keywords": ["keyword1", "keyword2"],
  "submission_req": {{"query_letter": true, "synopsis": false, "pages": 10}},
  "is_open": true,
  "wishlist_raw": "Raw wishlist text from the page",
  "bio_raw": "Raw bio text from the page",
  "hard_nos_raw": "Raw hard-nos text from the page",
  "email": "agent@agency.com or null",
  "response_time": "6-8 weeks or null",
  "country": "US or null"
}}

Rules:
- "name" is REQUIRED. Extract the agent's full name.
- "genres": Use lowercase_with_underscores. Standard names like: literary_fiction, commercial_fiction, science_fiction, fantasy, romance, mystery, thriller, horror, historical_fiction, young_adult, middle_grade, picture_books, memoir, narrative_nonfiction, self_help, biography, poetry, graphic_novels, womens_fiction, upmarket_fiction, speculative_fiction, contemporary_fiction, crime_fiction, suspense, paranormal, dystopian, adventure, humor, essay_collection, cookbooks, health_wellness, business, science, history, true_crime, travel, nature_writing, sports, music, art, philosophy, religion, politics, psychology, education, parenting, crafts_hobbies
- "keywords": Compact terms only (1-3 words each). NOT full sentences. Minimum 3 keywords. Examples: "diverse voices", "unreliable narrator", "found family", "magical realism"
- "hard_nos_keywords": Compact terms the agent does NOT want. Examples: "erotica", "fan fiction", "screenplays"
- "audience": From this list only: adult, ya, middle_grade, children, picture_books
- "wishlist_raw": Extract the full wishlist/MSWL text as a coherent block. If not found, use null.
- "bio_raw": Extract bio/about text as a coherent block. If not found, use null.
- "hard_nos_raw": Extract the full "what I don't want" text as a coherent block. If not found, use null.
- "is_open": true if accepting queries, false if closed, null if unclear
- "submission_req": JSON object with submission requirements (pages count, synopsis, query letter, etc.)
- For any field you cannot determine, use null (for strings/objects) or empty list [] (for arrays)

Profile text:
{clean_text}"""
