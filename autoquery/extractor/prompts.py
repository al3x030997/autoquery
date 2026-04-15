"""Versioned extraction prompts for L1 (Note-Taker) and the multi-agent roster pass."""
from pathlib import Path

PROMPT_VERSION = "2.0"

NOTE_TAKER_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "note_taker_v1.txt").read_text()

MULTI_AGENT_ROSTER_SYSTEM_PROMPT = """\
You are a data extraction specialist for literary agent profiles.
This page contains information about MULTIPLE literary agents at the same agency.
Extract only the agent names and agency metadata. Respond with valid JSON only — no markdown, no commentary."""

MULTI_AGENT_ROSTER_USER_PROMPT = """\
Extract the list of literary agents on this page.
Return JSON:

{{
  "agency_info": {{
    "name": "Agency name",
    "exclusive_query": true/false,
    "response_time": "2 months or null",
    "submission_url": "https://querymanager.com/... or null",
    "country": "US or null"
  }},
  "agents": [
    {{
      "name": "Agent Full Name",
      "section_hint": "first few words of their section"
    }}
  ]
}}

Rules:
- Extract EVERY agent named on the page
- "name" is REQUIRED for each agent — use their full name as written
- "section_hint": Copy the first 5-10 words of text that starts their individual section (bio, wishlist, etc.)
- Do NOT extract full profiles, genres, or wishlists — only names and section hints
- For agency-wide policies (response time, exclusive queries, submission portal), put them in "agency_info"
- For any field you cannot determine, use null

Page text:
{clean_text}"""
