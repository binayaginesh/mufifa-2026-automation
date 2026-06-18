#!/usr/bin/env python3
"""
μFIFA World Cup 2026 - Profile Validator
-----------------------------------------
Checks that a profile file in /profile/ meets all required structure rules.
Used by both the pre-commit hook (locally) and GitHub Actions CI (on PR).

Exit codes:
  0 - all checks passed
  1 - one or more checks failed
"""

import sys
import os
import re

# ── Colour helpers (disabled in CI if NO_COLOR is set) ──────────────────────
USE_COLOR = (os.environ.get("NO_COLOR") is None and sys.stdout.isatty()) or os.environ.get("GITHUB_ACTIONS") == "true"

def red(s):    return f"\033[31m{s}\033[0m" if USE_COLOR else s
def green(s):  return f"\033[32m{s}\033[0m" if USE_COLOR else s
def yellow(s): return f"\033[33m{s}\033[0m" if USE_COLOR else s
def bold(s):   return f"\033[1m{s}\033[0m"  if USE_COLOR else s

# ── Required top-level sections (## headings) ──────────────────────────────
REQUIRED_TOP_SECTIONS = [
    "## FIFA World Cup Corner",
    "## Portfolio Highlights",
]

# ── Required sections (must appear as #### headings) ────────────────────────
REQUIRED_SECTIONS = [
    "#### My Nation & Why:",
    "#### Supporting Team in the Real World Cup 2026:",
    "#### All-Time Favourite Player:",
    "#### Best Player Right Now:",
    "#### Past World Cup Memories:",
    "#### 2026 Predictions:",
    "#### μFIFA World Cup 2026 - Tournament Goals:",
    "#### History of Open Source and Collaborative Contributions:",
    "#### History of Community Engagement:",
    "#### Domain Profiles:",
    "#### Tools, Workflows & Automations:",
    "#### Public Portfolio & Recognition:",
    "#### Education and Proof of Work:",
    "#### History of Leadership:",
    "#### Networking:",
    "#### Career Plan:",
    "#### Profile Card:",
]

# ── Rules ────────────────────────────────────────────────────────────────────

def check_filename(path):
    """File must be named <something>@mulearn.md"""
    name = os.path.basename(path)
    if not re.match(r'^.+@mulearn\.md$', name, re.IGNORECASE):
        return False, f"File must be named <your-muid>@mulearn.md - got '{name}'"
    return True, f"Filename is valid: {name}"


def clean_heading_text(text):
    """
    Remove markdown heading symbols, bold/italic markup, colons, emojis,
    normalize mu/micro signs, and normalize spaces for robust comparison.
    """
    text = text.lower()
    text = text.replace("µ", "u").replace("μ", "u")
    # Replace dashes and hyphens with a space
    text = re.sub(r'[\-\u2013\u2014\u2212]', ' ', text)
    # Remove markdown formatting and colons
    text = re.sub(r'[#\*_\:]', '', text)
    # Keep alphanumeric characters, spaces, and ampersand/vertical bar/slash
    text = re.sub(r'[^a-z0-9\s\&\|\/]', '', text)
    return " ".join(text.split())


def is_horizontal_rule(line, prev_line_was_blank):
    """
    Check if a line is a horizontal rule. Supports Setext heading context.
    """
    line_strip = line.strip()
    if re.match(r'^\*{3,}\s*$', line_strip):
        return True
    if re.match(r'^[-_]{3,}\s*$', line_strip):
        if line_strip.startswith("_"):
            return True
        return prev_line_was_blank
    return False


def get_heading_level(line):
    line_strip = line.strip()
    m = re.match(r'^(#+)\s+', line_strip)
    if m:
        return len(m.group(1))
    return 99


def is_line_heading(line, clean_target):
    """
    Checks if a line is formatted as a heading and matches clean_target.
    """
    line_strip = line.strip()
    if not line_strip:
        return False
    if line_strip.startswith("- ") or (line_strip.startswith("* ") and not line_strip.startswith("**")):
        return False
    cleaned_line = clean_heading_text(line_strip)
    if cleaned_line != clean_target:
        return False
    if re.match(r'^#+\s+', line_strip):
        return True
    if line_strip.startswith("**") and line_strip.rstrip(":").endswith("**"):
        return True
    if len(line_strip) < 100:
        return True
    return False


def heading_exists(content, heading_name):
    """
    Returns True if heading_name exists as a heading in content.
    """
    clean_target = clean_heading_text(heading_name)
    for line in content.splitlines():
        if is_line_heading(line, clean_target):
            return True
    return False


def find_heading_line(content, heading_name):
    """
    Finds the actual matched heading line in the file content, returning it for messages.
    """
    clean_target = clean_heading_text(heading_name)
    for line in content.splitlines():
        if is_line_heading(line, clean_target):
            return line.strip()
    return heading_name


def extract_section(content, heading_name):
    """
    Extracts the content of a section.
    Returns the body text of the section if found, otherwise None.
    """
    lines = content.splitlines()
    clean_target = clean_heading_text(heading_name)
    
    start_idx = -1
    start_level = 99
    for idx, line in enumerate(lines):
        if is_line_heading(line, clean_target):
            start_idx = idx
            start_level = get_heading_level(line)
            break
            
    if start_idx == -1:
        return None
        
    all_headings = {clean_heading_text(h) for h in REQUIRED_SECTIONS + REQUIRED_TOP_SECTIONS + ["About Me"]}
    all_headings.discard(clean_target)
    
    section_lines = []
    prev_line_was_blank = False
    
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        line_strip = line.strip()
        
        # 1. Horizontal rule terminates the section
        if is_horizontal_rule(line, prev_line_was_blank):
            break
            
        # 2. Matches another required heading
        cleaned_line = clean_heading_text(line_strip)
        if cleaned_line in all_headings and is_line_heading(line, cleaned_line):
            break
            
        # 3. Heading level is equal or higher
        if line_strip.startswith("#"):
            level = get_heading_level(line)
            if start_level != 99:
                if level <= start_level:
                    break
            else:
                if level <= 2:
                    break
                    
        # Skip Setext style headings underlines if they immediately follow the start heading
        if idx == start_idx + 1 and re.match(r'^[-=]{3,}\s*$', line_strip):
            prev_line_was_blank = (line_strip == "")
            continue
            
        section_lines.append(line)
        prev_line_was_blank = (line_strip == "")
        
    return "\n".join(section_lines).strip()


def check_header(lines):
    """
    Validate the profile header.
    - Ignores blank lines.
    - Ignores UTF-8 BOM.
    - Title exists.
    - Squad Domain and FIFA Nation exist in the first few lines.
    - Validates Squad Domain value.
    """
    cleaned = []
    for line in lines:
        line = line.replace("\ufeff", "").strip()
        if line:
            cleaned.append(line)

    if not cleaned:
        return False, "File is empty"

    # Check that a title exists (first non-blank line)
    title_line = cleaned[0]
    if "squad domain" in title_line.lower() or "fifa nation" in title_line.lower():
        return False, f"Missing title. Found: {title_line!r}"

    squad_domain_line = None
    fifa_nation_line = None

    for line in cleaned[:10]:
        if "squad domain" in line.lower():
            squad_domain_line = line
        if "fifa nation" in line.lower():
            fifa_nation_line = line

    if not squad_domain_line:
        return False, "Missing Squad Domain"
    if not fifa_nation_line:
        return False, "Missing FIFA Nation"

    valid_domains = [
        "Coder",
        "Maker",
        "Designer",
        "Strategist"
    ]

    squad_domain_lower = squad_domain_line.lower()
    if not any(domain.lower() in squad_domain_lower for domain in valid_domains):
        return False, "Invalid Squad Domain"

    return True, "Header looks good"


def check_about_me(content):
    """
    About Me section must exist and contain at least 200 characters.
    """
    about_text = extract_section(content, "About Me")
    if about_text is None:
        return False, "'### About Me' section is missing"

    placeholder_patterns = [
        r'^\s*-\s*$',
        r'^\s*-\s*\.\.\.\s*$',
        r'^\s*-\s*N/A\s*$',
        r'^\s*-\s*TBD\s*$',
        r'^\s*-\s*write about your self',
        r'^\s*-\s*write about yourself',
        r'^\s*>\s*Who are you',
    ]

    about_lines = []
    for line in about_text.splitlines():
        line = line.strip()
        # Remove blockquote markers if present
        line = re.sub(r'^>\s*', '', line).strip()
        if not line:
            continue
        # Filter placeholders
        if any(re.match(p, line, re.IGNORECASE) for p in placeholder_patterns):
            continue
        # Filter comments and templates
        if line.startswith("<!--") or line.startswith("*If you're just starting") or line.startswith("- *If you're just starting"):
            continue
        about_lines.append(line)

    meaningful_text = "\n".join(about_lines).strip()
    char_count = len(meaningful_text)

    if char_count < 200:
        return False, (
            f"About Me must be at least 200 characters "
            f"- currently {char_count} characters"
        )

    return True, f"About Me is {char_count} characters ✓"


def check_top_sections(content):
    """Top-level section headings must be present"""
    errors = []
    for section in REQUIRED_TOP_SECTIONS:
        if not heading_exists(content, section):
            errors.append(f"Missing top-level section: {section}")
    if errors:
        return False, errors
    return True, "Top-level sections present"


def check_sections(content):
    """All required sections must be present"""
    errors = []
    for section in REQUIRED_SECTIONS:
        if not heading_exists(content, section):
            errors.append(f"Missing section: {section}")
    if errors:
        return False, errors
    return True, "All required sections present"


def check_domain_profiles(content):
    """
    Validate that Domain Profiles section contains at least one valid URL.
    """
    body = extract_section(content, "Domain Profiles")
    if body is None:
        return False, "Domain Profiles section is missing."
    
    # Match any valid http/https or www link
    urls = re.findall(r'(?:https?://|www\.)[^\s\)\`\]\>]+', body)
    if not urls:
        return False, "At least one public profile or portfolio link is required in the Domain Profiles section."
    
    return True, "Domain Profiles looks good"


def check_sections_not_empty(content, lines):
    """Each required section must have at least one non-empty, non-placeholder line after it"""
    warnings = []
    
    placeholder_patterns = [
        r'^\s*-\s*$',                          # bare dash
        r'^\s*-\s*\.\.\.\s*$',                 # - ...
        r'^\s*-\s*N/A\s*$',                    # - N/A
        r'^\s*-\s*TBD\s*$',                    # - TBD
        r'^\s*-\s*write about your self',       # copy-pasted from old template (variant)
        r'^\s*-\s*write about yourself',          # copy-pasted from old template
        r'^\s*>\s*Who are you',                 # un-edited About Me prompt
    ]

    for section in REQUIRED_SECTIONS:
        body = extract_section(content, section)
        if body is None:
            continue
            
        actual_heading = find_heading_line(content, section)
        
        if not body:
            warnings.append(f"Section appears empty: {actual_heading}")
            continue

        # Check if body is only placeholder lines
        body_lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("<!--")]
        non_placeholder = [
            l for l in body_lines
            if not any(re.match(p, l, re.IGNORECASE) for p in placeholder_patterns)
            and not l.strip().startswith("*If you're just starting")
            and not l.strip().startswith("- *If you're just starting")
        ]

        if not non_placeholder:
            warnings.append(f"Section looks unfilled (only placeholder text): {actual_heading}")

    if warnings:
        return "warn", warnings
    return True, "All sections have content"


def check_profile_card(content):
    """Profile card img src must be updated from the placeholder"""
    placeholder = "yourname@mulearn"
    img_match = re.search(r'src="https://mulearn\.org/embed/rank/([^"]+)"', content)
    if not img_match:
        return False, "Profile Card img tag is missing or malformed - check the Profile Card section"
    if placeholder in img_match.group(1):
        return False, "Profile Card still has the placeholder URL - replace 'yourname@mulearn' with your actual MUID"
    return True, f"Profile Card embed found: {img_match.group(1)}"


def check_mulearn_id_consistency(path, content):
    """The MUID in the filename should match the one in the profile card src"""
    filename_muid = os.path.basename(path).replace(".md", "").replace(".MD", "")
    img_match = re.search(r'src="https://mulearn\.org/embed/rank/([^"]+)"', content)
    if not img_match:
        return True, "Skipped MUID consistency check (no img found)"
    
    card_muid = img_match.group(1)
    if filename_muid.lower() != card_muid.lower():
        return False, (
            f"MUID mismatch: filename is '{filename_muid}' "
            f"but profile card uses '{card_muid}' - they must match"
        )
    return True, f"MUID is consistent: {filename_muid}"


# ── Runner ───────────────────────────────────────────────────────────────────

def validate(path):
    print(bold(f"\nμFIFA Profile Validator → {os.path.basename(path)}"))
    print("─" * 55)

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(red(f"✗ File not found: {path}"))
        return False

    lines = content.splitlines()
    passed = True
    has_warnings = False

    checks = [
        ("Filename",             lambda: check_filename(path)),
        ("Header",               lambda: check_header(lines)),
        ("About Me length",      lambda: check_about_me(content)),
        ("Top-level sections",   lambda: check_top_sections(content)),
        ("Required sections",    lambda: check_sections(content)),
        ("Domain Profiles",      lambda: check_domain_profiles(content)),
        ("Section content",      lambda: check_sections_not_empty(content, lines)),
        ("Profile Card",         lambda: check_profile_card(content)),
        ("MUID consistency",     lambda: check_mulearn_id_consistency(path, content)),
    ]

    for label, fn in checks:
        result = fn()
        status, detail = result[0], result[1]

        if status is True:
            print(green(f"  ✓ {label}"))
        elif status == "warn":
            has_warnings = True
            print(yellow(f"  ⚠ {label}"))
            items = detail if isinstance(detail, list) else [detail]
            for item in items:
                print(yellow(f"      → {item}"))
        else:
            passed = False
            print(red(f"  ✗ {label}"))
            items = detail if isinstance(detail, list) else [detail]
            for item in items:
                print(red(f"      → {item}"))

    print("─" * 55)
    if passed and not has_warnings:
        print(green("  All checks passed. You're on the pitch! ⚽\n"))
    elif passed and has_warnings:
        print(yellow("  Passed with warnings - fill in the flagged sections before your PR.\n"))
    else:
        print(red("  Validation failed. Fix the errors above before submitting your PR.\n"))

    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <profile_file.md> [<file2.md> ...]")
        sys.exit(1)

    all_passed = True
    for filepath in sys.argv[1:]:
        if not validate(filepath):
            all_passed = False

    sys.exit(0 if all_passed else 1)
