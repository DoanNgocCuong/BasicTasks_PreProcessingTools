import json
from pathlib import Path


def sort_queries_in_config(config_path: Path) -> None:
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # The JSON structure has an outer list "search_queries" with one object
    # that again contains a "search_queries" list of strings. We sort that inner list.
    if not isinstance(data, dict):
        raise ValueError("Root of config must be a JSON object")

    outer_list = data.get("search_queries")
    if not isinstance(outer_list, list) or not outer_list:
        raise ValueError("Expected non-empty list at data['search_queries']")

    first_item = outer_list[0]
    if not isinstance(first_item, dict):
        raise ValueError("Expected first element of data['search_queries'] to be an object")

    inner_queries = first_item.get("search_queries")
    if not isinstance(inner_queries, list):
        raise ValueError("Expected list at data['search_queries'][0]['search_queries']")

    # Sort by length, then lexicographically as a tie-breaker
    inner_queries_sorted = sorted(inner_queries, key=lambda s: (len(s), s))
    first_item["search_queries"] = inner_queries_sorted

    # Write back preserving 2-space indentation and UTF-8 without escaping non-ASCII
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    config_file = Path(__file__).with_name("crawler_config.json")
    sort_queries_in_config(config_file)


