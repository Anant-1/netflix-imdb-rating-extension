#!/usr/bin/env python3
"""
CLI Test script to verify movie lookup directly from terminal
Usage:
    python3 test_lookup.py "Inception"
    python3 test_lookup.py "Breaking Bad"
"""
import sys
from server import lookup_movie, init_db

def main():
    init_db()
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Inception"

    print(f"\n🔎 Testing IMDb lookup for: '{query}'...")
    data = lookup_movie(query)
    if data:
        print("\n✅ Movie Found!")
        print(f"  • Title:      {data.get('title')}")
        print(f"  • Year:       {data.get('year')}")
        print(f"  • IMDb ID:    {data.get('imdb_id')}")
        print(f"  • Rating:     ★ {data.get('rating')} / 10")
        print(f"  • Votes:      {data.get('votes')}")
        print(f"  • Genre:      {data.get('genre')}")
        print(f"  • Plot:       {data.get('plot')[:120]}..." if data.get('plot') else "  • Plot:       N/A")
        print(f"  • Cached:     {data.get('cached')}")
        print(f"  • Source:     {data.get('source')}\n")
    else:
        print(f"\n❌ Could not find rating for '{query}'\n")

if __name__ == "__main__":
    main()
