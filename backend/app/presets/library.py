from __future__ import annotations

from dataclasses import dataclass

from app.experiments.input_generator import InputKind, InputProfile


@dataclass(frozen=True, slots=True)
class PresetAlgorithmDefinition:
    slug: str
    name: str
    category: str
    summary: str
    description: str
    language: str
    input_kind: InputKind
    input_profile: InputProfile
    expected_complexity: str
    starter_code: str
    tags: tuple[str, ...]
    default_input_sizes: tuple[int, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "slug": self.slug,
            "name": self.name,
            "category": self.category,
            "summary": self.summary,
            "description": self.description,
            "language": self.language,
            "input_kind": self.input_kind,
            "input_profile": self.input_profile,
            "expected_complexity": self.expected_complexity,
            "starter_code": self.starter_code,
            "tags": list(self.tags),
            "default_input_sizes": list(self.default_input_sizes),
            "notes": list(self.notes),
        }


PRESET_ALGORITHMS: tuple[PresetAlgorithmDefinition, ...] = (
    PresetAlgorithmDefinition(
        slug="linear-search",
        name="Linear Search",
        category="searching",
        summary="Scan a list once to find a value.",
        description="A simple baseline for showing O(n) behavior and how every item contributes to runtime.",
        language="python",
        input_kind="array",
        input_profile="random",
        expected_complexity="O(n)",
        starter_code=(
            "def linear_search(items, target):\n"
            "    for index, value in enumerate(items):\n"
            "        if value == target:\n"
            "            return index\n"
            "    return -1\n"
            "\n"
            "items = list(map(int, input().split()))\n"
            "target = int(input())\n"
            "print(linear_search(items, target))\n"
        ),
        tags=("baseline", "loops", "search"),
        default_input_sizes=(10, 100, 1000, 5000),
        notes=("Great for comparing against binary search.", "Useful for visible line-count growth."),
    ),
    PresetAlgorithmDefinition(
        slug="binary-search",
        name="Binary Search",
        category="searching",
        summary="Find an item in sorted data by repeatedly halving the search space.",
        description="A canonical logarithmic example that is easy to contrast with linear search.",
        language="python",
        input_kind="array",
        input_profile="sorted",
        expected_complexity="O(log n)",
        starter_code=(
            "def binary_search(items, target):\n"
            "    left, right = 0, len(items) - 1\n"
            "    while left <= right:\n"
            "        mid = (left + right) // 2\n"
            "        if items[mid] == target:\n"
            "            return mid\n"
            "        if items[mid] < target:\n"
            "            left = mid + 1\n"
            "        else:\n"
            "            right = mid - 1\n"
            "    return -1\n"
        ),
        tags=("search", "divide-and-conquer", "sorted-input"),
        default_input_sizes=(16, 128, 1024, 8192),
        notes=("Requires sorted input.", "Highlights branching and shrinking search windows."),
    ),
    PresetAlgorithmDefinition(
        slug="bubble-sort",
        name="Bubble Sort",
        category="sorting",
        summary="Repeatedly swap neighboring elements until the array is ordered.",
        description="An intentionally inefficient sorting baseline that demonstrates nested loop growth.",
        language="python",
        input_kind="array",
        input_profile="reversed",
        expected_complexity="O(n^2)",
        starter_code=(
            "def bubble_sort(items):\n"
            "    items = list(items)\n"
            "    n = len(items)\n"
            "    for i in range(n):\n"
            "        for j in range(0, n - i - 1):\n"
            "            if items[j] > items[j + 1]:\n"
            "                items[j], items[j + 1] = items[j + 1], items[j]\n"
            "    return items\n"
        ),
        tags=("sorting", "nested-loops", "quadratic"),
        default_input_sizes=(10, 50, 100, 250),
        notes=("Useful for line heatmaps.", "Pairs well with merge sort comparisons."),
    ),
    PresetAlgorithmDefinition(
        slug="merge-sort",
        name="Merge Sort",
        category="sorting",
        summary="Recursively split input and merge sorted halves.",
        description="A divide-and-conquer sorting algorithm with O(n log n) behavior and recursion depth visibility.",
        language="python",
        input_kind="array",
        input_profile="random",
        expected_complexity="O(n log n)",
        starter_code=(
            "def merge_sort(items):\n"
            "    if len(items) <= 1:\n"
            "        return list(items)\n"
            "    mid = len(items) // 2\n"
            "    left = merge_sort(items[:mid])\n"
            "    right = merge_sort(items[mid:])\n"
            "    merged = []\n"
            "    i = j = 0\n"
            "    while i < len(left) and j < len(right):\n"
            "        if left[i] <= right[j]:\n"
            "            merged.append(left[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            merged.append(right[j])\n"
            "            j += 1\n"
            "    merged.extend(left[i:])\n"
            "    merged.extend(right[j:])\n"
            "    return merged\n"
        ),
        tags=("sorting", "recursion", "divide-and-conquer"),
        default_input_sizes=(16, 128, 1024, 8192),
        notes=("Good contrast against bubble sort.", "Shows recursion and merge overhead."),
    ),
    PresetAlgorithmDefinition(
        slug="recursive-fibonacci",
        name="Recursive Fibonacci",
        category="recursion",
        summary="Naive recursive Fibonacci to show exponential blowup.",
        description="A classic example for recursion trees, repeated calls, and exponential growth.",
        language="python",
        input_kind="numbers",
        input_profile="random",
        expected_complexity="O(2^n)",
        starter_code=(
            "def fibonacci(n):\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    return fibonacci(n - 1) + fibonacci(n - 2)\n"
            "\n"
            "n = int(input())\n"
            "print(fibonacci(n))\n"
        ),
        tags=("recursion", "exponential", "hotspot"),
        default_input_sizes=(5, 10, 20, 30),
        notes=("Use small sizes only.", "Great for call count visualizations."),
    ),
    PresetAlgorithmDefinition(
        slug="memoized-fibonacci",
        name="Memoized Fibonacci",
        category="dynamic-programming",
        summary="Cache recursive Fibonacci results to collapse repeated work.",
        description="A strong demonstration of how memoization changes runtime shape while keeping recursion readable.",
        language="python",
        input_kind="numbers",
        input_profile="random",
        expected_complexity="O(n)",
        starter_code=(
            "def fibonacci(n, memo=None):\n"
            "    if memo is None:\n"
            "        memo = {}\n"
            "    if n in memo:\n"
            "        return memo[n]\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    memo[n] = fibonacci(n - 1, memo) + fibonacci(n - 2, memo)\n"
            "    return memo[n]\n"
        ),
        tags=("dynamic-programming", "memoization", "recursion"),
        default_input_sizes=(10, 20, 50, 100),
        notes=("Pairs well with recursive Fibonacci.", "Shows the effect of caching."),
    ),
)


def list_preset_categories() -> list[dict[str, object]]:
    categories: dict[str, dict[str, object]] = {}
    for preset in PRESET_ALGORITHMS:
        category = categories.setdefault(
            preset.category,
            {
                "slug": preset.category,
                "name": preset.category.replace("-", " ").title(),
                "description": f"Algorithms grouped under {preset.category}.",
                "preset_count": 0,
            },
        )
        category["preset_count"] = int(category["preset_count"]) + 1
    return sorted(categories.values(), key=lambda item: str(item["slug"]))


def get_preset_definition(slug: str) -> PresetAlgorithmDefinition | None:
    for preset in PRESET_ALGORITHMS:
        if preset.slug == slug:
            return preset
    return None
