"""
Text Cleaner — Strips site chrome (nav, footer, sidebar) from captured agent page text.

Reads raw innerText files from page_capture, outputs clean profile text
ready for LLM extraction.

Usage:
    python -m autoquery.simulation.text_cleaner --input-dir ./capture_output/text_content --output-dir ./capture_output/cleaned
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Lines that appear in MSWL site navigation / header area
NAV_LINES = {
    "skip to content",
    "member login",
    "find agents + editors",
    "find agents",
    "search guide",
    "genre/name search",
    "recently updated",
    "keyword search",
    "agents",
    "editors",
    "consultations",
    "apply for a profile",
    "resources and events for agents and editors",
    "event calendar",
    "brought to you by",
    "the manuscript academy",
    "about mswl",
    "getting started",
    "faq + terms of service",
    "faq + terms of use",
    "press",
    "blog",
    "contact",
    "resources",
    "podcast",
    "agent consultations",
    "join",
}

# Lines that appear in footer area
FOOTER_LINES = {
    "member login",
    "reset your password",
    "faq + terms of use",
    "faq + terms of service",
}

# Isolated sidebar UI labels to remove (only when they appear as standalone short lines)
SIDEBAR_LABELS = {
    "guidelines & details",
    "vital info",
    "website",
    "agent",
}


class TextCleaner:
    """Strips site chrome from captured agent page text."""

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def clean_batch(self) -> dict:
        """Clean all .txt files in input_dir. Returns summary stats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        txt_files = sorted(self.input_dir.glob("*.txt"))
        if not txt_files:
            logger.error("No .txt files found in %s", self.input_dir)
            return {"total": 0, "success": 0, "failed": 0}

        total = len(txt_files)
        success = 0
        failed = 0

        for i, input_path in enumerate(txt_files, 1):
            logger.info("[%d/%d] Cleaning %s...", i, total, input_path.name)
            try:
                cleaned = self.clean_file(input_path)
                output_path = self.output_dir / input_path.name
                output_path.write_text(cleaned, encoding="utf-8")
                success += 1
            except Exception as exc:
                failed += 1
                logger.error("[%d/%d] Failed %s: %s", i, total, input_path.name, exc)

        logger.info("Cleaning complete: %d/%d succeeded, %d failed", success, total, failed)
        return {"total": total, "success": success, "failed": failed}

    def clean_file(self, input_path: Path) -> str:
        """Clean a single text file. Returns cleaned text."""
        raw = input_path.read_text(encoding="utf-8")
        lines = raw.splitlines()

        lines = self._strip_header(lines)
        lines = self._strip_footer(lines)
        lines = self._strip_sidebar_residue(lines)
        lines = self._collapse_blank_lines(lines)

        return "\n".join(lines).strip() + "\n"

    def _strip_header(self, lines: list[str]) -> list[str]:
        """Remove site navigation lines from the top."""
        start = 0
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if not stripped:
                continue
            if stripped in NAV_LINES:
                start = i + 1
                continue
            # Stop scanning once we hit a non-nav, non-empty line
            break

        return lines[start:]

    def _strip_footer(self, lines: list[str]) -> list[str]:
        """Remove footer lines from the bottom."""
        end = len(lines)

        # Scan from bottom
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].strip().lower()
            if not stripped:
                end = i
                continue
            if stripped in FOOTER_LINES:
                end = i
                continue
            if stripped.startswith("copyright ©") or "all rights reserved" in stripped:
                end = i
                continue
            # Hit real content, stop
            break

        return lines[:end]

    def _strip_sidebar_residue(self, lines: list[str]) -> list[str]:
        """Remove isolated sidebar UI labels."""
        result = []
        for line in lines:
            stripped = line.strip().lower()
            if stripped in SIDEBAR_LABELS and len(stripped) < 30:
                continue
            result.append(line)
        return result

    def _collapse_blank_lines(self, lines: list[str]) -> list[str]:
        """Collapse runs of 3+ blank lines down to 1."""
        result = []
        blank_count = 0
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 1:
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)
        return result


async def main():
    parser = argparse.ArgumentParser(
        description="Clean captured agent page text by removing site chrome."
    )
    parser.add_argument(
        "--input-dir", required=True, help="Directory with raw .txt files"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Directory for cleaned .txt output"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    cleaner = TextCleaner(input_dir=args.input_dir, output_dir=args.output_dir)
    cleaner.clean_batch()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
