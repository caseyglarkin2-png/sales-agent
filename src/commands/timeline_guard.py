#!/usr/bin/env python3
"""Timeline guard: Fail if docs contain timeline language.

This script checks specified markdown files for forbidden timeline words
and exits non-zero if any are found.

Usage:
    python -m src.commands.timeline_guard docs/GO_LIVE_TONIGHT.md
    python -m src.commands.timeline_guard --all-docs
"""
import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Forbidden words/phrases (case-insensitive)
FORBIDDEN_PATTERNS = [
    r'\bweek\b',
    r'\bweeks\b',
    r'\bday\b',
    r'\bdays\b',
    r'\bmonth\b',
    r'\bmonths\b',
    r'\btimeline\b',
    r'\beta\b',
    r'\bestimate\b',
    r'\bduration\b',
    r'\bprepared:\b',
    r'\bphase\s*\d+\b',  # "Phase 4", "Phase 5", etc.
    r'\bsprint\b',
    r'\bsprints\b',
    r'\bquarter\b',
    r'\bq[1-4]\b',
    r'\bbudget\b',
    r'\bstaffing\b',
    r'\bheadcount\b',
]

# Exceptions (allowed in specific contexts)
EXCEPTIONS = [
    r'business\s+days?',  # "2 business days" for task due dates is OK
    r'near-term',  # describing availability is OK
    r'30-minute',  # describing meeting slots is OK
]


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """Check a file for forbidden timeline language.
    
    Returns list of (line_number, line_content, matched_pattern) tuples.
    """
    violations = []
    
    try:
        content = filepath.read_text()
    except Exception as e:
        print(f"ERROR: Cannot read {filepath}: {e}", file=sys.stderr)
        return violations
    
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        # Skip code blocks
        if line.strip().startswith('```') or line.strip().startswith('`'):
            continue
        
        # Check for exceptions first
        line_lower = line.lower()
        has_exception = any(re.search(exc, line_lower) for exc in EXCEPTIONS)
        
        for pattern in FORBIDDEN_PATTERNS:
            match = re.search(pattern, line_lower)
            if match and not has_exception:
                violations.append((line_num, line.strip(), match.group()))
    
    return violations


def main():
    parser = argparse.ArgumentParser(description='Check docs for timeline language')
    parser.add_argument('files', nargs='*', help='Files to check')
    parser.add_argument('--all-docs', action='store_true', 
                        help='Check all markdown files in docs/')
    args = parser.parse_args()
    
    files_to_check = []
    
    if args.all_docs:
        docs_dir = Path('docs')
        if docs_dir.exists():
            files_to_check.extend(docs_dir.glob('*.md'))
    
    if args.files:
        files_to_check.extend(Path(f) for f in args.files)
    
    if not files_to_check:
        print("No files specified. Use --all-docs or provide file paths.")
        sys.exit(1)
    
    total_violations = 0
    
    for filepath in files_to_check:
        if not filepath.exists():
            print(f"WARNING: File not found: {filepath}", file=sys.stderr)
            continue
        
        violations = check_file(filepath)
        
        if violations:
            print(f"\n❌ TIMELINE VIOLATIONS in {filepath}:")
            for line_num, line, matched in violations:
                print(f"  Line {line_num}: '{matched}' in: {line[:80]}...")
            total_violations += len(violations)
        else:
            print(f"✓ {filepath}: No timeline language found")
    
    if total_violations > 0:
        print(f"\n❌ FAILED: {total_violations} timeline violation(s) found")
        print("Remove timeline language (weeks, days, months, ETA, etc.) and retry.")
        sys.exit(1)
    else:
        print(f"\n✓ PASSED: No timeline language in checked files")
        sys.exit(0)


if __name__ == '__main__':
    main()
