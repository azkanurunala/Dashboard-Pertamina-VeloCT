import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, Tag
import pandas as pd


# Constants

# Month name → zero-padded month number.
# Covers both Indonesian and English full/abbreviated names (all lowercase).
# All lookups call .lower() on the parsed token before checking this map.
MONTH_NAME_MAP: dict[str, str] = {
    # Indonesian
    "januari":   "01", "februari": "02", "maret":    "03", "april":    "04",
    "mei":       "05", "juni":     "06", "juli":     "07", "agustus":  "08",
    "september": "09", "oktober":  "10", "november": "11", "desember": "12",
    # English full
    "january": "01", "february": "02", "march":   "03",
    "may":     "05", "june":     "06", "july":    "07", "august": "08",
    "october": "10",
    # English abbreviated
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}

# Keep the old name as an alias so existing scrapers don't break
INDONESIAN_MONTHS = MONTH_NAME_MAP


# Date Utilities

def parse_month_name_date(raw_text: str) -> str | None:
    """
    Convert a ``"DD MonthName YYYY"`` date string to ISO format (YYYY-MM-DD).

    Supports both Indonesian and English month names (full and abbreviated),
    as defined in ``MONTH_NAME_MAP``. Searches for the pattern anywhere inside
    ``raw_text``, so the input does not need to be pre-trimmed.

    Parameters
    ----------
    raw_text : str
        Raw date string, e.g. ``"29 Agustus 2025"``, ``"29 August 2025"``,
        ``"29 Aug 2025"``, or a subtitle like ``"29 Agustus 2025 • Siaran Pers"``.

    Returns
    -------
    str | None
        ISO-formatted date (``YYYY-MM-DD``), or ``None`` if the input is
        empty, ``"N/A"``, or does not contain a recognisable date.

    Examples
    --------
    >>> parse_month_name_date("29 Agustus 2025")
    '2025-08-29'
    >>> parse_month_name_date("29 August 2025")
    '2025-08-29'
    >>> parse_month_name_date("29 Aug 2025")
    '2025-08-29'
    >>> parse_month_name_date("invalid")
    None
    """
    if not raw_text or raw_text.strip() == "N/A":
        return None

    match = re.search(r"(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})", raw_text)
    if not match:
        return None

    day   = match.group(1).zfill(2)
    month = MONTH_NAME_MAP.get(match.group(2).lower())
    year  = match.group(3)

    if not month:
        return None  # Unrecognised month name

    return f"{year}-{month}-{day}"


# Keep the old name as an alias so existing scrapers (BI, BPS) don't break
parse_indonesian_date = parse_month_name_date


def normalize_to_iso_date(date_input: str) -> str | None:
    """
    Normalise a date string of any supported format to ISO (YYYY-MM-DD).

    Supported input formats
    -----------------------
    - ISO date already:      ``"2025-08-29"``
    - DD-MM-YYYY:            ``"29-08-2025"``
    - Indonesian long form:  ``"29 Agustus 2025"``
    - English long form:     ``"29 August 2025"``
    - Month DD, YYYY:        ``"January 12, 2026"``  (Bioenergytimes format)
    - Abbreviated English:   ``"29 Aug 2025"``

    Parameters
    ----------
    date_input : str
        Date string in one of the supported formats.

    Returns
    -------
    str | None
        ISO-formatted date string, or ``None`` if no format matched.

    Examples
    --------
    >>> normalize_to_iso_date("2025-08-29")
    '2025-08-29'
    >>> normalize_to_iso_date("29-08-2025")
    '2025-08-29'
    >>> normalize_to_iso_date("29 Agustus 2025")
    '2025-08-29'
    >>> normalize_to_iso_date("January 12, 2026")
    '2026-01-12'
    >>> normalize_to_iso_date("29 Aug 2025")
    '2025-08-29'
    """
    if not date_input:
        return None

    # Already ISO
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_input.strip()):
        return date_input.strip()

    # DD-MM-YYYY (e.g. "29-08-2025" — used by Tempo scraper)
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", date_input.strip()):
        dd, mm, yy = date_input.strip().split("-")
        return f"{yy}-{mm}-{dd}"

    # Indonesian or English long/abbreviated form (e.g. "29 Agustus 2025", "29 Aug 2025")
    result = parse_month_name_date(date_input)
    if result:
        return result

    # "Month DD, YYYY" (e.g. "January 12, 2026" — used by Bioenergytimes)
    try:
        return datetime.strptime(date_input.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Abbreviated English form (e.g. "29 Aug 2025")
    try:
        return datetime.strptime(date_input.strip(), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        pass

    return None


# HTML Content Utilities

def extract_clean_paragraphs(
    html_content: str | Tag,
    boilerplate_keywords: list[str] | None = None,
    min_length: int = 30,
    min_threshold: int = 5,
) -> str:
    """
    Extract and clean body text from an HTML string or BeautifulSoup tag.

    Parses all ``<p>`` tags and applies three filtering steps:

    1. **Length gate** — paragraphs shorter than ``min_threshold`` chars
       are silently dropped (likely empty tags or single symbols).
    2. **Boilerplate filter** — paragraphs containing any keyword from
       ``boilerplate_keywords`` are dropped (e.g. contact info, footers).
    3. **Minimum length** — paragraphs shorter than ``min_length`` chars
       are dropped as likely captions or labels.

    Parameters
    ----------
    html_content : str | BeautifulSoup Tag
        Raw HTML string or a pre-parsed BeautifulSoup ``Tag`` / ``BeautifulSoup``
        object from which ``<p>`` tags will be extracted.
    boilerplate_keywords : list[str] | None, optional
        Case-insensitive substrings that identify boilerplate paragraphs to
        discard. Defaults to a general set suitable for Indonesian government
        press-release pages:
        ``["narahubung", "contact", "telp", "fax", "email", "@bps.go.id",
           "jl.", "jakarta", "departemen komunikasi"]``
    min_length : int, optional
        Minimum character count for a paragraph to be kept. Defaults to 30.
    min_threshold : int, optional
        Paragraphs strictly shorter than this value are discarded without
        checking boilerplate rules. Defaults to 5.

    Returns
    -------
    str
        Cleaned paragraph text joined by double newlines, or an empty string
        if no valid paragraphs remain.

    Examples
    --------
    >>> html = "<p>Good content here.</p><p>Narahubung: 021-xxx</p>"
    >>> extract_clean_paragraphs(html)
    'Good content here.'
    """
    if boilerplate_keywords is None:
        boilerplate_keywords = [
            "narahubung", "contact", "telp", "fax", "email",
            "@bps.go.id", "jl.", "jakarta", "departemen komunikasi",
        ]

    # Accept either a raw HTML string or an already-parsed Tag
    if isinstance(html_content, str):
        soup = BeautifulSoup(html_content, "html.parser")
    else:
        soup = html_content

    valid_chunks: list[str] = []

    for p in soup.find_all("p"):
        text = p.get_text(strip=True)

        # Silently discard near-empty tags
        if not text or len(text) < min_threshold:
            continue

        # Discard boilerplate paragraphs (case-insensitive keyword match)
        text_lower = text.lower()
        if any(kw.lower() in text_lower for kw in boilerplate_keywords):
            continue

        # Discard paragraphs that are too short to be meaningful body text
        if len(text) < min_length:
            continue

        valid_chunks.append(text)

    return "\n\n".join(valid_chunks)


# Relative Date Resolution

def resolve_relative_date(raw_text: str, reference: datetime | None = None) -> str | None:
    """
    Resolve an Indonesian relative date expression to ISO format (YYYY-MM-DD).

    Handles the following patterns (case-insensitive):

    - ``"X tahun lalu"``  — X years ago  (approximated as X * 365 days)
    - ``"X bulan lalu"``  — X months ago (approximated as X * 30 days)
    - ``"X minggu lalu"`` — X weeks ago
    - ``"X hari lalu"``   — X days ago
    - ``"X jam [Y menit] yang lalu"`` — X hours and/or Y minutes ago

    If the input does not match any relative pattern, returns ``None`` so
    the caller can fall through to an absolute-date parser.

    Parameters
    ----------
    raw_text : str
        Raw date string from the page, e.g. ``"3 hari lalu"`` or
        ``"2 jam 15 menit yang lalu"``.
    reference : datetime | None, optional
        The point in time from which offsets are calculated.
        Defaults to ``datetime.now()``.

    Returns
    -------
    str | None
        ISO-formatted date string (``YYYY-MM-DD``), or ``None`` if
        ``raw_text`` does not contain a recognised relative pattern.

    Examples
    --------
    >>> from datetime import datetime
    >>> resolve_relative_date("3 hari lalu", reference=datetime(2025, 8, 29))
    '2025-08-26'
    >>> resolve_relative_date("29 Agustus 2025")  # not a relative date
    None
    """
    if not raw_text:
        return None

    now  = reference or datetime.now()
    text = raw_text.strip().lower()

    # --- Years ---
    m = re.search(r"(\d+)\s*tahun", text)
    if m:
        return (now - timedelta(days=int(m.group(1)) * 365)).strftime("%Y-%m-%d")

    # --- Months ---
    m = re.search(r"(\d+)\s*bulan", text)
    if m:
        return (now - timedelta(days=int(m.group(1)) * 30)).strftime("%Y-%m-%d")

    # --- Weeks ---
    m = re.search(r"(\d+)\s*minggu", text)
    if m:
        return (now - timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")

    # --- Days ---
    m = re.search(r"(\d+)\s*hari", text)
    if m:
        return (now - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    # --- Hours and/or minutes ("X jam Y menit yang lalu") ---
    if "yang lalu" in text:
        hours   = int(mh.group(1)) if (mh := re.search(r"(\d+)\s*jam",   text)) else 0
        minutes = int(mm.group(1)) if (mm := re.search(r"(\d+)\s*menit", text)) else 0
        return (now - timedelta(hours=hours, minutes=minutes)).strftime("%Y-%m-%d")

    return None  # Input is not a relative date expression


# DOM Container Detection

def find_best_container(
    soup: BeautifulSoup | Tag,
    child_tags: list[str] | None = None,
    min_items: int = 3,
    list_class_keywords: list[str] | None = None,
) -> Tag | None:
    """
    Find the ``<div>`` that contains the highest count of direct child items.

    Scans all ``<div>`` elements in ``soup`` and returns the one that has the
    most direct ``<section>`` or ``<article>`` children (configurable via
    ``child_tags``). This heuristic reliably identifies article-list containers
    and article-content containers across different page layouts.

    When multiple candidates share the same item count, the one with fewer
    total links is preferred (likely the more tightly-scoped container).

    Parameters
    ----------
    soup : BeautifulSoup | Tag
        Parsed HTML document or subtree to search within.
    child_tags : list[str] | None, optional
        HTML tag names to count as "items". Defaults to ``["section", "article"]``.
    min_items : int, optional
        Minimum number of child items a ``<div>`` must contain to be a
        candidate. Defaults to 3.
    list_class_keywords : list[str] | None, optional
        Class name substrings that boost confidence a div is a list container.
        Defaults to ``["list", "grid", "container", "content"]``.

    Returns
    -------
    Tag | None
        The best-matching ``<div>`` element, or ``None`` if no candidate met
        the ``min_items`` threshold.
    """
    child_tags           = child_tags or ["section", "article"]
    list_class_keywords  = list_class_keywords or ["list", "grid", "container", "content"]
    candidates: list[dict] = []

    for div in soup.find_all("div"):
        items = sum(len(div.find_all(tag, recursive=False)) for tag in child_tags)
        if items < min_items:
            continue

        class_str        = " ".join(div.get("class", [])).lower()
        has_list_keyword = any(kw in class_str for kw in list_class_keywords)

        candidates.append({
            "element":          div,
            "items":            items,
            "links":            len(div.find_all("a", href=True)),
            "has_list_keyword": has_list_keyword,
        })

    if not candidates:
        return None

    # Primary sort: most child items; secondary: has a list-class keyword;
    # tertiary: fewest total links (tighter scope)
    best = max(candidates, key=lambda c: (c["items"], c["has_list_keyword"], -c["links"]))
    return best["element"]


def find_content_container(soup: BeautifulSoup | Tag, min_paragraphs: int = 3) -> Tag | None:
    """
    Find the ``<div>`` with the highest number of ``<p>`` descendants.

    Used to locate the article body container on an article detail page when
    no reliable CSS class is known in advance.

    Parameters
    ----------
    soup : BeautifulSoup | Tag
        Parsed HTML document or subtree to search within.
    min_paragraphs : int, optional
        Minimum ``<p>`` count a ``<div>`` must contain to be a candidate.
        Defaults to 3.

    Returns
    -------
    Tag | None
        The ``<div>`` with the most ``<p>`` tags, or ``None`` if no candidate
        met the threshold.
    """
    candidates = [
        {"element": div, "paragraphs": len(div.find_all("p"))}
        for div in soup.find_all("div")
        if len(div.find_all("p")) >= min_paragraphs
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda c: c["paragraphs"])["element"]


def find_pagination_container(
    soup: BeautifulSoup | Tag,
    min_links: int = 3,
) -> Tag | None:
    """
    Detect the pagination ``<div>`` by inspecting link patterns.

    A valid pagination container must satisfy all three conditions:

    1. Contains at least ``min_links`` anchor tags with ``href`` attributes.
    2. Has at least two consecutive page numbers starting from 1
       (e.g. links labelled ``1``, ``2``, ``3``).
    3. At least one anchor ``href`` contains a ``?page=N`` or ``&page=N``
       query parameter.

    When multiple candidates qualify, the one with the most page-number links
    is chosen. Among ties, the one with fewest total links is preferred
    (narrowest scope).

    Parameters
    ----------
    soup : BeautifulSoup | Tag
        Parsed HTML document or subtree to search within.
    min_links : int, optional
        Minimum number of anchor tags required in a candidate div.
        Defaults to 3.

    Returns
    -------
    Tag | None
        The best-matching pagination ``<div>``, or ``None`` if none was found.
    """
    candidates: list[dict] = []

    for div in soup.find_all("div"):
        links = div.find_all("a", href=True)
        if len(links) < min_links:
            continue

        # Collect integer page numbers visible as link text
        page_numbers = sorted(
            int(a.get_text(strip=True))
            for a in links
            if a.get_text(strip=True).isdigit()
        )

        # Must start at 1 and have at least 2 consecutive numbers
        if not page_numbers or page_numbers[0] != 1 or len(page_numbers) < 2:
            continue

        consecutive = sum(
            1 for i in range(len(page_numbers) - 1)
            if page_numbers[i + 1] - page_numbers[i] == 1
        ) + 1
        if consecutive < 2:
            continue

        # Must have at least one href with a ?page= or &page= parameter
        has_page_param = any(
            re.search(r"[?&]page=\d+", a.get("href", "")) for a in links
        )
        if not has_page_param:
            continue

        candidates.append({
            "element":      div,
            "link_count":   len(links),
            "page_numbers": page_numbers,
        })

    if not candidates:
        return None

    # Prefer the container with the most page-number links (most complete
    # pagination); break ties by choosing the one with fewest total links
    best = max(candidates, key=lambda c: (len(c["page_numbers"]), -c["link_count"]))
    return best["element"]


def get_total_pages_from_pagination(pagination_element: Tag | None) -> int:
    """
    Read the highest page number from a pagination element.

    Inspects both the ``href`` query parameters (``?page=N``) and the visible
    link text of all anchors inside ``pagination_element``.

    Parameters
    ----------
    pagination_element : Tag | None
        A BeautifulSoup ``Tag`` representing the pagination container, as
        returned by ``find_pagination_container``. If ``None``, returns 1.

    Returns
    -------
    int
        The highest page number found, or 1 if the element is ``None`` or
        no numeric page references are found.
    """
    if not pagination_element:
        return 1

    max_page = 1

    for a in pagination_element.find_all("a", href=True):
        # Check href query parameter
        m = re.search(r"[?&]page=(\d+)", a.get("href", ""))
        if m:
            max_page = max(max_page, int(m.group(1)))

        # Check visible link text
        text = a.get_text(strip=True)
        if text.isdigit():
            max_page = max(max_page, int(text))

    return max_page


# XML Utilities

def get_element_text(element) -> str:
    """
    Safely extract all text content from an XML element.

    Concatenates text from the element and all its descendants using
    ``itertext()``, then strips leading/trailing whitespace.

    This is the standard way to read text from ``xml.etree.ElementTree``
    elements, which do not support ``.text_content()`` like lxml does.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element | None
        An XML element, or ``None``.

    Returns
    -------
    str
        Concatenated text content, or an empty string if the element is
        ``None`` or contains no text.

    Examples
    --------
    >>> import xml.etree.ElementTree as ET
    >>> el = ET.fromstring("<title>Hello <b>World</b></title>")
    >>> get_element_text(el)
    'Hello World'
    >>> get_element_text(None)
    ''
    """
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


# DataFrame Utilities

# Mapping from scraper-internal column names to project-standard English names.
# Each scraper may use a subset of these keys; unmapped columns are left as-is.
_STANDARD_COLUMN_MAP: dict[str, str] = {
    # Indonesian internal keys
    "judul":   "title",
    "tanggal": "date",
    "link":    "url",
    "konten":  "content",
    # Title-case variants (used by Kompas scraper)
    "Judul":   "title",
    "Tanggal": "date",
    "Link":    "url",
    "Konten":  "content",
}


def rename_to_standard_columns(df) -> "pd.DataFrame":
    """
    Rename scraper-internal column names to the project-standard English names.

    Applies ``_STANDARD_COLUMN_MAP`` to the DataFrame, renaming only the
    columns that are present; all other columns are left unchanged.

    Standard output columns
    -----------------------
    - ``title``   ← judul / Judul
    - ``date``    ← tanggal / Tanggal
    - ``url``     ← link / Link
    - ``content`` ← konten / Konten

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame produced by any scraper module, with raw internal column names.

    Returns
    -------
    pd.DataFrame
        A copy of ``df`` with columns renamed according to the standard map.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame([{"judul": "A", "link": "http://x.com", "tanggal": "2025-01-01"}])
    >>> rename_to_standard_columns(df).columns.tolist()
    ['title', 'url', 'date']
    """
    # Only rename columns that are actually present in the DataFrame
    applicable = {k: v for k, v in _STANDARD_COLUMN_MAP.items() if k in df.columns}
    return df.rename(columns=applicable)


# XML News Sitemap Utilities

# Standard XML namespace declarations for Google News sitemaps.
# Used by extract_news_sitemap_entry() and importable by any sitemap scraper.
NS_SITEMAP: dict[str, str] = {"sm":   "http://www.sitemaps.org/schemas/sitemap/0.9"}
NS_NEWS:    dict[str, str] = {"news": "http://www.google.com/schemas/sitemap-news/0.9"}


def extract_news_sitemap_entry(url_tag) -> dict | None:
    """
    Extract article metadata from a single ``<url>`` element in a Google News sitemap.

    Reads the canonical link from ``<sm:loc>`` and title, publication date,
    and keywords from the ``<news:news>`` extension block (Google News Sitemap
    Protocol). The publication date is normalised to ISO date (``YYYY-MM-DD``)
    by stripping the time portion from RFC 3339 timestamps.

    This function covers the identical logic previously duplicated across
    the Kompas and Kontan scrapers.

    Parameters
    ----------
    url_tag : xml.etree.ElementTree.Element
        A ``<url>`` element from a parsed article sitemap XML document.

    Returns
    -------
    dict | None
        Dict with keys:

        - ``title``    — article headline (``"(No Title)"`` if absent)
        - ``link``     — canonical article URL
        - ``pubdate``  — raw publication datetime string from the sitemap
        - ``date``     — ISO date portion only (``YYYY-MM-DD``)
        - ``keywords`` — comma-separated keyword string (empty if absent)

        Returns ``None`` if no valid ``<sm:loc>`` link is found.

    Examples
    --------
    >>> # Given a <url> element with <sm:loc> and <news:news> children:
    >>> info = extract_news_sitemap_entry(url_tag)
    >>> info["date"]
    '2025-08-29'
    """
    loc_tag = url_tag.find("sm:loc", NS_SITEMAP)
    link    = get_element_text(loc_tag)
    if not link:
        return None

    news_tag    = url_tag.find("news:news", NS_NEWS)
    title       = ""
    pubdate_raw = ""
    keywords    = ""

    if news_tag is not None:
        title       = get_element_text(news_tag.find("news:title",            NS_NEWS))
        pubdate_raw = get_element_text(news_tag.find("news:publication_date", NS_NEWS))
        keywords    = get_element_text(news_tag.find("news:keywords",         NS_NEWS))

    # Fallback: use <sm:lastmod> if <news:publication_date> is absent.
    # Some Kontan sub-sitemaps omit <news:news> entirely but still carry a
    # <lastmod> value — without this fallback those articles get date = "-"
    # and can never be matched by a date filter.
    if not pubdate_raw:
        lastmod = url_tag.find("sm:lastmod", NS_SITEMAP)
        pubdate_raw = get_element_text(lastmod)

    # Strip the time portion from RFC 3339 timestamps (e.g. "2025-08-29T07:00:00+07:00")
    date_only = pubdate_raw.split("T")[0] if "T" in pubdate_raw else pubdate_raw or "-"

    return {
        "title":    title or "(No Title)",
        "link":     link,
        "pubdate":  pubdate_raw,
        "date":     date_only,
        "keywords": keywords,
    }


def clean_scraped_text(
    text: str,
    extra_patterns: list[str] | None = None,
    strip_url_lines: bool = False,
    strip_control_chars: bool = False,
) -> str:
    """
    Remove common boilerplate patterns from scraped article text.

    Always strips the following patterns (case-insensitive, including all
    text that follows on the same and subsequent lines):

    - ``"Baca Juga ..."``
    - ``"Cek Berita dan Artikel ..."``

    Additional site-specific patterns can be supplied via ``extra_patterns``.
    Collapses 3 or more consecutive blank lines into 2.

    Parameters
    ----------
    text : str
        Raw article text extracted from ``<p>`` or ``<li>`` elements.
    extra_patterns : list[str] | None, optional
        Additional regex patterns to strip (each anchored to remove the
        matched text and everything after it on the same+subsequent lines).
        Defaults to None.
    strip_url_lines : bool, optional
        If ``True``, removes any line that consists entirely of a URL
        (i.e. starts with ``http://`` or ``https://`` after stripping
        whitespace). Useful for sites that inject bare links into content.
        Defaults to ``False``.
    strip_control_chars : bool, optional
        If ``True``, removes ASCII control characters (``\\x00–\\x1f``,
        excluding ``\\t``, ``\\n``, ``\\r``) and high-byte control chars
        (``\\x7f–\\x9f``). Useful for sites that embed invisible characters
        in article text (e.g. The Guardian). Defaults to ``False``.

    Returns
    -------
    str
        Cleaned text, or the original value unchanged if it is empty or
        ``"N/A"``.

    Examples
    --------
    >>> clean_scraped_text("Good content.\\n\\nBaca Juga: some link")
    'Good content.'
    >>> clean_scraped_text("Text.\\n\\nhttps://example.com", strip_url_lines=True)
    'Text.'
    >>> clean_scraped_text("Text.\\n\\nCustom noise.", extra_patterns=["Custom noise"])
    'Text.'
    """
    if not text or text == "N/A":
        return text

    # Built-in boilerplate patterns common across Indonesian news sites
    builtin_patterns = [
        r"Baca Juga.*",
        r"Cek Berita dan Artikel.*",
    ]

    all_patterns = builtin_patterns + (extra_patterns or [])

    for pattern in all_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    # Optional: remove lines that are bare URLs
    if strip_url_lines:
        lines = [
            line for line in text.splitlines()
            if not re.match(r"^\s*https?://", line.strip())
        ]
        text = "\n".join(lines)

    # Optional: strip ASCII control characters and high-byte control chars
    # (e.g. embedded \x00-\x08 or \x7f-\x9f from some sites like The Guardian)
    if strip_control_chars:
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# General List Utilities

def dedup_by_key(items: list[dict], key: str) -> list[dict]:
    """
    Remove duplicate dicts from a list, keeping the first occurrence of each
    unique value for the given ``key``.

    Parameters
    ----------
    items : list[dict]
        List of dicts to deduplicate.
    key : str
        Dict key whose value is used as the uniqueness criterion (e.g. ``"link"``).

    Returns
    -------
    list[dict]
        Deduplicated list in original order, excluding items where ``key``
        is missing or empty.

    Examples
    --------
    >>> items = [{"link": "a"}, {"link": "b"}, {"link": "a"}]
    >>> dedup_by_key(items, "link")
    [{'link': 'a'}, {'link': 'b'}]
    """
    seen: set = set()
    out:  list[dict] = []
    for item in items:
        value = item.get(key)
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(item)
    return out


# RSS Feed Utilities

def fetch_rss_entries(feed_url: str, limit: int = 50) -> list[dict]:
    """
    Fetch and parse a single RSS feed, returning normalised article entries.

    Uses ``feedparser`` to parse the feed and extracts title, link, ISO
    publication date, and summary for each entry. Prints the entry count
    for visibility.

    Parameters
    ----------
    feed_url : str
        Full URL of the RSS feed to fetch.
    limit : int, optional
        Maximum number of entries to return. Defaults to 50.

    Returns
    -------
    list[dict]
        List of article dicts with keys:

        - ``title``   — article headline
        - ``link``    — canonical article URL
        - ``tanggal`` — ISO date string (``YYYY-MM-DD``), or empty string
        - ``summary`` — raw RSS summary/description text

    Raises
    ------
    requests.HTTPError
        If the HTTP request to ``feed_url`` fails.

    Notes
    -----
    Requires ``feedparser`` to be installed (``pip install feedparser``).
    """
    import feedparser  # Optional dependency — imported lazily

    import requests as _requests
    _HEADERS = {"User-Agent": "Mozilla/5.0"}

    response = _requests.get(feed_url, headers=_HEADERS, timeout=20)
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    print(f"[RSS] {feed_url} → {len(feed.entries)} entries")

    entries: list[dict] = []
    for entry in feed.entries[:limit]:
        title   = getattr(entry, "title",   "").strip()
        link    = getattr(entry, "link",    "").strip()
        summary = (
            getattr(entry, "summary",     "") or
            getattr(entry, "description", "") or ""
        )

        date = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            from datetime import datetime as _dt
            date = _dt(*entry.published_parsed[:6]).strftime("%Y-%m-%d")

        entries.append({
            "title":   title,
            "link":    link,
            "tanggal": date,
            "summary": summary,
        })

    return entries


# Paragraph Validation

# Spam keywords that identify non-content paragraphs (cookie notices,
# subscription prompts, social-follow CTAs, etc.)
_SPAM_KEYWORDS: tuple[str, ...] = (
    "cookie", "privacy policy", "terms of service", "subscribe",
    "sign up", "newsletter", "follow us", "advertisement",
)


def is_valid_paragraph(
    text: str,
    min_length: int = 10,
    extra_spam_keywords: tuple[str, ...] | list[str] | None = None,
) -> bool:
    """
    Return True if ``text`` looks like a real content paragraph.

    Rejects paragraphs that are:
    - Empty or shorter than ``min_length`` characters
    - Composed entirely of digits, whitespace, and punctuation (e.g. dates,
      page numbers)
    - Containing common spam/boilerplate keywords (cookie notices,
      subscription prompts, newsletter CTAs, etc.)
    - Containing any site-specific keywords supplied via ``extra_spam_keywords``

    Parameters
    ----------
    text : str
        Paragraph text to validate (should already be stripped).
    min_length : int, optional
        Minimum number of characters required. Defaults to 10.
    extra_spam_keywords : tuple | list | None, optional
        Additional site-specific spam keywords to reject (case-insensitive
        substring match). These are checked in addition to the built-in
        ``_SPAM_KEYWORDS``. Example Guardian extras:
        ``("photograph:", "skip past newsletter", "privacy notice:")``

    Returns
    -------
    bool
        ``True`` if the paragraph appears to be valid content.

    Examples
    --------
    >>> is_valid_paragraph("This is a real paragraph about energy policy.")
    True
    >>> is_valid_paragraph("Sign up for our newsletter")
    False
    >>> is_valid_paragraph("12 - 3, 4.")
    False
    >>> is_valid_paragraph("Hi")
    False
    >>> is_valid_paragraph("Photograph: Reuters", extra_spam_keywords=("photograph:",))
    False
    """
    if not text or len(text) < min_length:
        return False

    text_lower = text.lower()

    # Reject built-in spam/boilerplate content
    if any(kw in text_lower for kw in _SPAM_KEYWORDS):
        return False

    # Reject site-specific extra spam keywords
    if extra_spam_keywords and any(kw in text_lower for kw in extra_spam_keywords):
        return False

    # Reject lines that are purely numeric/punctuation (timestamps, page refs)
    if re.match(r"^[\d\s\-:,\.]+$", text):
        return False

    return True