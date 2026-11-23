
"""Natural language preprocessing and intent detection for JALNETRA."""

from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz, process


# ============================================================
# 1. LANGUAGE NORMALIZATION
# ============================================================

LANGUAGE_MAP = {
    # Marathi
    "पूर्व मानसून": "pre monsoon",
    "पूर्वमोसमी": "pre monsoon",
    "प्री मानसून": "pre monsoon",
    "उत्तर मानसून": "post monsoon",
    "पोस्ट मानसून": "post monsoon",
    "भविष्यवाणी": "forecast",
    "भविष्य": "forecast",
    "अंदाज": "forecast",
    "जिल्ह्यांची": "district",
    "जिल्ह्यांचा": "district",
    "जिल्हा": "district",
    "तालुक्यांची": "taluka",
    "तालुक्यांचा": "taluka",
    "तालुका": "taluka",
    "पुनर्भरण": "recharge",
    "उपसा": "extraction",
    "ऐतिहासिक": "historical",
    "कल": "trend",
    "ग्राफ": "graph",
    "आलेख": "graph",
    "जिल्हे": "districts",
    "तालुके": "talukas",
    "पाणी": "water",
    "भूजल": "groundwater",
    "जलस्तर": "level",
    "पातळी": "level",
    "माहिती": "data",
    "तुलना": "compare",
    "क्रमवारी": "ranking",
    "सर्वाधिक": "highest",
    "कमी": "lowest",
    "सुरक्षित": "safe",
    "अति दोहन": "over exploited",
    "अतिदोहन": "over exploited",
    "अर्ध गंभीर": "semi critical",
    "अर्धगंभीर": "semi critical",
    "गंभीर": "critical",
    "धोकादायक": "risk",

    # Hindi
    "जिला": "district",
    "जिलों": "districts",
    "तहसील": "taluka",
    "तहसीलों": "talukas",
    "पूर्वानुमान": "forecast",
    "अनुमान": "forecast",
    "रिचार्ज": "recharge",
    "निकासी": "extraction",
    "रुझान": "trend",
    "तुलना": "compare",
    "राज्य": "state",
    "जलस्तर": "level",
    "भूजल": "groundwater",
    "सुरक्षित": "safe",
    "अतिदोहित": "over exploited",
    "गंभीर": "critical",
    "अर्ध गंभीर": "semi critical",

    # English synonyms
    "prediction": "forecast",
    "predictions": "forecast",
    "predict": "forecast",
    "predicting": "forecast",
    "forecasting": "forecast",
    "future": "forecast",
    "versus": "vs",
    "comparison": "compare",
    "compare": "compare",
    "ranking": "rank",
    "rankings": "rank",
    "top": "rank",
    "highest": "highest",
    "maximum": "highest",
    "lowest": "lowest",
    "minimum": "lowest",
    "bottom": "lowest",
    "withdrawal": "extraction",
    "withdrawals": "extraction",
    "usage": "extraction",
    "historical": "historical",
    "historically": "historical",
    "visualization": "graph",
    "visualisation": "graph",
    "visualize": "graph",
    "visualise": "graph",
    "chart": "graph",
    "plot": "graph",
    "graphs": "graph",
}


def preprocess_query(query: str) -> str:
    """
    Normalize English, Marathi and Hindi queries into a
    consistent English keyword representation.

    Example:
        'पुणे जिल्ह्याची तुलना करा'
        -> 'पुणे district compare करा'
    """
    text = str(query or "").casefold().strip()

    # Replace longer phrases first to avoid partial replacements.
    for source in sorted(LANGUAGE_MAP, key=len, reverse=True):
        replacement = LANGUAGE_MAP[source]

        pattern = (
            r"(?<!\w)"
            + re.escape(source.casefold())
            + r"(?!\w)"
        )

        text = re.sub(pattern, replacement, text)

    # Normalize punctuation and whitespace.
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# 2. GENERAL TEXT HELPERS
# ============================================================

def _normalize_text(value: Any) -> str:
    """Normalize a value for matching."""
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def _get_unique_entities(df, column: str) -> list[str]:
    """Safely retrieve unique non-empty entity names."""
    if df is None or not hasattr(df, "columns"):
        return []

    if column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    return sorted(
        [value for value in values if value],
        key=len,
        reverse=True,
    )


def _find_exact_entities(query: str, entities: list[str]) -> list[str]:
    """
    Find exact entity names in a query.

    Longer entity names are checked first to avoid matching
    a shorter name inside a longer name.
    """
    text = _normalize_text(query)
    matches = []

    for entity in sorted(entities, key=len, reverse=True):
        normalized = _normalize_text(entity)

        if not normalized:
            continue

        pattern = (
            r"(?<!\w)"
            + re.escape(normalized)
            + r"(?!\w)"
        )

        match = re.search(pattern, text)

        if match:
            matches.append({
                "entity": entity,
                "start": match.start(),
                "end": match.end(),
            })

    # Preserve query order while removing overlapping matches.
    matches.sort(key=lambda item: item["start"])

    selected = []
    occupied_ranges = []

    for match in matches:
        overlaps = any(
            match["start"] < end and match["end"] > start
            for start, end in occupied_ranges
        )

        if overlaps:
            continue

        selected.append(match["entity"])
        occupied_ranges.append((match["start"], match["end"]))

    return selected


def _fuzzy_entity_match(
    query: str,
    entities: list[str],
    score_cutoff: int = 88,
) -> str | None:
    """
    Find a likely entity using fuzzy matching on query phrases.

    Unlike matching the complete sentence, this compares entity
    names against individual word windows.

    Ambiguous matches are rejected.
    """
    if not query or not entities:
        return None

    words = re.findall(r"\w+", _normalize_text(query), flags=re.UNICODE)

    if not words:
        return None

    candidates = {}

    for entity in entities:
        entity_words = re.findall(
            r"\w+",
            _normalize_text(entity),
            flags=re.UNICODE,
        )

        if not entity_words:
            continue

        entity_length = len(entity_words)
        best_score = 0

        # Compare the entity against phrases of similar length.
        min_length = max(1, entity_length - 1)
        max_length = min(len(words), entity_length + 1)

        for window_size in range(min_length, max_length + 1):
            for start in range(len(words) - window_size + 1):
                phrase = " ".join(words[start:start + window_size])

                score = fuzz.ratio(
                    _normalize_text(entity),
                    phrase,
                )

                best_score = max(best_score, score)

        candidates[entity] = best_score

    if not candidates:
        return None

    ranked = sorted(
        candidates.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    best_entity, best_score = ranked[0]

    if best_score < score_cutoff:
        return None

    # Reject ambiguous matches where two candidates score similarly.
    if len(ranked) > 1:
        second_score = ranked[1][1]

        if best_score - second_score < 4:
            return None

    return best_entity


# ============================================================
# 3. YEAR EXTRACTION
# ============================================================

def extract_year(query: str) -> int | None:
    """
    Extract a four-digit year.

    Supports historical years such as 1970 and future years
    such as 2030.
    """
    text = str(query or "")

    match = re.search(
        r"(?<!\d)(?:19|20)\d{2}(?!\d)",
        text,
    )

    return int(match.group()) if match else None


# ============================================================
# 4. TOP-N EXTRACTION
# ============================================================

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def extract_top_n(query: str, default: int = 10) -> int:
    """
    Extract the requested number of ranking results.

    Supports:
        top 5 districts
        rank 10 talukas
        bottom 5 districts
        show 5 highest districts
        10 lowest talukas
        top five districts
    """
    text = preprocess_query(query)

    patterns = [
        r"\b(?:top|rank|bottom|first|last)\s+(\d+)\b",
        r"\b(\d+)\s+(?:highest|lowest|districts?|talukas?)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return max(1, int(match.group(1)))

    for word, number in NUMBER_WORDS.items():
        patterns = [
            rf"\b(?:top|rank|bottom|first|last)\s+{word}\b",
            rf"\b{word}\s+(?:highest|lowest|districts?|talukas?)\b",
        ]

        if any(re.search(pattern, text) for pattern in patterns):
            return number

    return default


# ============================================================
# 5. DISTRICT EXTRACTION
# ============================================================

def extract_district(query: str, df) -> str | None:
    """
    Extract a district name from a query.

    Exact matching is preferred. Fuzzy matching is used only
    when an exact match is not available.
    """
    districts = _get_unique_entities(df, "District")

    if not districts:
        return None

    exact_matches = _find_exact_entities(query, districts)

    if exact_matches:
        return exact_matches[0]

    if len(str(query or "").strip()) < 4:
        return None

    return _fuzzy_entity_match(
        query,
        districts,
        score_cutoff=88,
    )


# ============================================================
# 6. TALUKA EXTRACTION
# ============================================================

def extract_taluka(query: str, df) -> str | None:
    """
    Extract a taluka name from a query.

    Note:
        A taluka name may occur in multiple districts.
        This function returns the name only. The chatbot should
        use the selected district context to resolve ambiguity.
    """
    talukas = _get_unique_entities(df, "Taluka")

    if not talukas:
        return None

    exact_matches = _find_exact_entities(query, talukas)

    if exact_matches:
        return exact_matches[0]

    if len(str(query or "").strip()) < 4:
        return None

    return _fuzzy_entity_match(
        query,
        talukas,
        score_cutoff=88,
    )


# ============================================================
# 7. STATE EXTRACTION
# ============================================================

def extract_state(query: str, df) -> str | None:
    """Extract a state name from a query."""
    states = _get_unique_entities(df, "State")

    if not states:
        return None

    exact_matches = _find_exact_entities(query, states)

    return exact_matches[0] if exact_matches else None


# ============================================================
# 8. DISTRICT COMPARISON EXTRACTION
# ============================================================

def extract_districts_for_compare(
    query: str,
    df,
) -> list[str]:
    """
    Extract up to two district names for comparison.

    Exact matches are preferred. If only one exact match is
    found, a second district may be resolved using fuzzy matching.

    Returns an empty list if two reliable districts cannot be
    identified.
    """
    districts = _get_unique_entities(df, "District")

    if len(districts) < 2:
        return []

    exact_matches = _find_exact_entities(query, districts)

    if len(exact_matches) >= 2:
        return exact_matches[:2]

    if len(str(query or "").strip()) < 4:
        return []

    remaining = [
        district
        for district in districts
        if district not in exact_matches
    ]

    fuzzy_match = _fuzzy_entity_match(
        query,
        remaining,
        score_cutoff=90,
    )

    if fuzzy_match and exact_matches:
        return exact_matches[:1] + [fuzzy_match]

    # Do not guess two districts from a sentence that contains
    # no reliable district names.
    return []


# ============================================================
# 9. INTENT DETECTION
# ============================================================

def _contains_any(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    """Check whether any complete phrase occurs in the text."""
    for phrase in phrases:
        pattern = (
            r"(?<!\w)"
            + re.escape(phrase)
            + r"(?!\w)"
        )

        if re.search(pattern, text):
            return True

    return False


def detect_intent(query: str) -> str:
    """
    Detect the primary intent of a user query.

    Possible return values:
        forecast
        risk
        compare
        rank
        trend
        graph
        state
        pre_monsoon
        post_monsoon
        recharge
        extractable
        extraction
        stage
        category
        data
        help
        general
    """
    text = preprocess_query(query)

    if not text:
        return "general"

    # --------------------------------------------------------
    # Help
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "help",
            "examples",
            "what can you do",
            "how to use",
        ],
    ):
        return "help"

    # --------------------------------------------------------
    # Comparison
    # Higher priority than trend, ranking and graph.
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "compare",
            "comparison",
            "vs",
            "versus",
            "difference between",
        ],
    ):
        return "compare"

    # --------------------------------------------------------
    # Forecast
    # --------------------------------------------------------
    if (
        _contains_any(
            text,
            [
                "forecast",
                "predict",
                "prediction",
                "future",
                "projected",
                "projection",
                "next 5",
                "next five",
            ],
        )
        or bool(re.search(r"\b20(?:2[6-9]|[3-9]\d)\b", text))
    ):
        return "forecast"

    # --------------------------------------------------------
    # Risk analysis
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "risk",
            "at risk",
            "high risk",
            "danger",
            "vulnerable",
            "over exploited",
            "over-exploited",
            "critical districts",
            "critical areas",
            "water stress",
        ],
    ):
        return "risk"

    # --------------------------------------------------------
    # Ranking
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "rank",
            "ranking",
            "top",
            "highest",
            "lowest",
            "maximum",
            "minimum",
            "bottom",
            "most",
            "least",
        ],
    ):
        return "rank"

    # --------------------------------------------------------
    # Historical trends
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "trend",
            "historical",
            "history",
            "over time",
            "year wise",
            "year-wise",
            "yearly trend",
            "change over time",
            "historical trend",
        ],
    ):
        return "trend"

    # --------------------------------------------------------
    # Graph / chart requests
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "graph",
            "chart",
            "plot",
            "visualization",
            "visualisation",
            "visualize",
            "visualise",
            "draw",
            "show graph",
        ],
    ):
        return "graph"

    # --------------------------------------------------------
    # State-level queries
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "state",
            "maharashtra",
        ],
    ):
        return "state"

    # --------------------------------------------------------
    # Seasonal queries
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "pre monsoon",
            "before monsoon",
            "pre-monsoon",
        ],
    ):
        return "pre_monsoon"

    if _contains_any(
        text,
        [
            "post monsoon",
            "after monsoon",
            "post-monsoon",
        ],
    ):
        return "post_monsoon"

    # --------------------------------------------------------
    # Groundwater metrics
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "recharge",
            "annual recharge",
            "groundwater recharge",
        ],
    ):
        return "recharge"

    if _contains_any(
        text,
        [
            "extractable",
            "extractable resource",
            "available resource",
        ],
    ):
        return "extractable"

    if _contains_any(
        text,
        [
            "extraction",
            "withdrawal",
            "water usage",
            "groundwater usage",
        ],
    ):
        return "extraction"

    if _contains_any(
        text,
        [
            "stage",
            "extraction stage",
            "groundwater development stage",
        ],
    ):
        return "stage"

    # --------------------------------------------------------
    # Category queries
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "category",
            "categories",
            "safe",
            "critical",
            "semi critical",
            "semi-critical",
            "over exploited",
            "over-exploited",
        ],
    ):
        return "category"

    # --------------------------------------------------------
    # General data queries
    # --------------------------------------------------------
    if _contains_any(
        text,
        [
            "data",
            "table",
            "records",
            "show",
            "list",
            "details",
            "information",
        ],
    ):
        return "data"

    return "general"


# ============================================================
# 10. METRIC DETECTION
# ============================================================

def detect_metric(query: str) -> str | None:
    """
    Resolve a metric using the existing utils.py implementation.

    Keeping this function delegated to resolve_metric() ensures
    that metric names remain consistent with the rest of JALNETRA.
    """
    from utils import resolve_metric

    return resolve_metric(preprocess_query(query))


# ============================================================
# 11. RANKING DIRECTION
# ============================================================

def is_ascending_rank(query: str) -> bool:
    """
    Return True when the user requests ascending order.

    Examples:
        lowest recharge
        bottom 5 districts
        least extraction
        minimum groundwater level
    """
    text = preprocess_query(query)

    return _contains_any(
        text,
        [
            "lowest",
            "bottom",
            "least",
            "minimum",
            "min",
        ],
    )


# ============================================================
# 12. COUNT QUERY DETECTION
# ============================================================

def is_count_query(query: str) -> bool:
    """Detect queries requesting a count or total."""
    text = preprocess_query(query)

    return _contains_any(
        text,
        [
            "how many",
            "count",
            "number of",
            "total",
            "quantity of",
        ],
    )


# ============================================================
# 13. GROUNDWATER CATEGORY FILTER
# ============================================================

def detect_category_filter(query: str) -> str | None:
    """
    Detect a groundwater assessment category.

    Standardized return values:
        Over-Exploited
        Semi-Critical
        Critical
        Safe
    """
    text = preprocess_query(query)

    category_patterns = [
        (
            "Over-Exploited",
            [
                "over exploited",
                "over-exploited",
                "overexploited",
            ],
        ),
        (
            "Semi-Critical",
            [
                "semi critical",
                "semi-critical",
                "semicritical",
            ],
        ),
        (
            "Critical",
            [
                "critical",
            ],
        ),
        (
            "Safe",
            [
                "safe",
            ],
        ),
    ]

    for category, patterns in category_patterns:
        if _contains_any(text, patterns):
            return category

    return None
