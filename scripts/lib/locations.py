"""US state mapping and city CSV loading."""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("serper")

US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def get_state_locations(state_codes: List[str]) -> List[str]:
    """Convert state codes to Serper location strings."""
    locations = []
    for code in state_codes:
        code_upper = code.upper().strip()
        if code_upper in US_STATE_NAMES:
            locations.append(f"{US_STATE_NAMES[code_upper]}, United States")
        else:
            locations.append(f"{code}, United States")
    return locations


def load_cities(cities_path: Path) -> List[Dict[str, str]]:
    """Load cities from CSV."""
    if not cities_path.exists():
        logger.warning(f"Cities file not found: {cities_path}")
        return []
    cities = []
    try:
        with open(cities_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cities.append(row)
    except Exception as e:
        logger.error(f"Error loading cities: {e}")
    return cities


def filter_cities_by_states(
    cities: List[Dict[str, str]],
    states: List[str],
    limit_per_state: Optional[int] = None,
) -> List[str]:
    """Filter cities matching the given states. Optionally limit per state."""
    states_lower = [s.lower() for s in states]
    state_buckets: Dict[str, List[str]] = {s: [] for s in states_lower}

    for city in cities:
        city_str = city.get("city", "") or city.get("location", "")
        for state in states_lower:
            if state in city_str.lower():
                state_buckets[state].append(city_str)
                break

    result = []
    for state in states_lower:
        bucket = state_buckets[state]
        if limit_per_state:
            result.extend(bucket[:limit_per_state])
        else:
            result.extend(bucket)

    return result
