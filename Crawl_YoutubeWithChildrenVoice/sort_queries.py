import json
from pathlib import Path


def sort_queries_in_config(config_path: Path) -> None:
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # The crawler expects root-level key "search_queries" to be a flat list of strings.
    # Current file may have been nested as: { "search_queries": [ { ..., "search_queries": [strings] } ] }
    # We normalize to a flat list, then sort by length + lexicographic tie-breaker.
    if not isinstance(data, dict):
        raise ValueError("Root of config must be a JSON object")

    root_sq = data.get("search_queries")
    normalized_queries = None
    if isinstance(root_sq, list) and root_sq and isinstance(root_sq[0], dict) and "search_queries" in root_sq[0]:
        inner = root_sq[0].get("search_queries")
        if not isinstance(inner, list):
            raise ValueError("Expected list at data['search_queries'][0]['search_queries']")
        normalized_queries = inner
    elif isinstance(root_sq, list):
        normalized_queries = root_sq
    else:
        raise ValueError("Expected list at data['search_queries']")

    # Clean and validate strings
    cleaned = []
    for i, q in enumerate(normalized_queries):
        if not isinstance(q, str):
            raise ValueError(f"search_queries[{i}] is not a string")
        s = q.strip()
        if not s:
            continue
        cleaned.append(s)

    # Sort by length, then lexicographically as a tie-breaker
    cleaned_sorted = sorted(cleaned, key=lambda s: (len(s), s))

    # Flatten back into the root per crawler expectation
    data["search_queries"] = cleaned_sorted

    # Write back preserving 2-space indentation and UTF-8 without escaping non-ASCII
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    config_file = Path(__file__).with_name("crawler_config.json")
    sort_queries_in_config(config_file)


