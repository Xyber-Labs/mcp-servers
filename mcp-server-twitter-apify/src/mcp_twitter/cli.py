from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

from mcp_twitter.config import AppSettings
from mcp_twitter.models import OutputFormat, QueryDefinition, QueryType
from mcp_twitter.queries import (
    build_default_registry,
    create_profile_query,
    create_replies_query,
    create_topic_query,
)
from mcp_twitter.registry import QueryRegistry
from mcp_twitter.scraper import TwitterScraper


def _print_types(registry: QueryRegistry) -> None:
    print("Available query types:")
    descriptions: dict[str, str] = {
        "topic": "Search tweets by keyword/topic (supports --sort Top/Latest, --only-verified, --only-image).",
        "profile": "Search tweets from a specific username (supports --since/--until date filters).",
        "replies": "Fetch replies for a thread via conversation_id.",
    }
    examples: dict[str, str] = {
        "topic": 'python -m mcp_twitter --topic "starlink" --sort Top --max-items 50',
        "profile": "python -m mcp_twitter --profile elonmusk --max-items 100",
        "replies": "python -m mcp_twitter --replies 1728108619189874825 --max-items 50",
    }

    print("-" * 90)
    for q_type in registry.types():
        desc = descriptions.get(q_type, "")
        ex = examples.get(q_type, "")
        print(f"  {q_type:8} ({len(registry.by_type(q_type))} preset)  {desc}")
        if ex:
            print(f"           e.g. {ex}")
    print("-" * 90)


def _print_queries(registry: QueryRegistry, query_type: QueryType | None = None) -> None:
    header = f"Available {query_type} queries:" if query_type else "Available queries:"
    print(header)
    print("-" * 70)
    for q in registry.list_queries(query_type=query_type):
        print(f"  [{q.type}] {q.id}. {q.name}")
    print("-" * 70)


def _run_queries(scraper: TwitterScraper, queries: Iterable[QueryDefinition]) -> list[Path]:
    saved: list[Path] = []
    for q in queries:
        print(f"\n=== [{q.type}] {q.id}. {q.name} ===")
        try:
            saved.append(scraper.run_query(q))
        except Exception as e:
            print(f"❌ Error running query {q.id}: {e}")
    if saved:
        print(f"\n✅ All results saved to '{scraper.results_dir}' directory")
        print("📚 Docs: https://apify.com/apidojo/twitter-scraper-lite")
    return saved


def _load_apify_token() -> str:
    settings = AppSettings()
    token = settings.apify.apify_token
    if not token:
        raise RuntimeError(
            "APIFY_TOKEN not found in environment variables or .env file. "
            "Please set APIFY_TOKEN in your .env file or as an environment variable."
        )
    return token


def build_parser(registry: QueryRegistry) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Twitter scraper using Apify - Select queries by type or create custom searches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all query types
  python -m main --list-types

  # List all queries
  python -m main --list

  # List queries of a specific type
  python -m main --list --type topic

  # Run all queries
  python -m main --all

  # Run all queries of a specific type
  python -m main --type topic

  # Run specific queries by ID
  python -m main 1 3 5

  # Create custom topic search
  python -m main --topic "AI news" --max-items 50

  # Create custom profile search
  python -m main --profile elonmusk --max-items 200

  # Create profile search with date range
  python -m main --profile elonmusk --since 2025-12-01 --until 2025-12-31

  # Create replies search
  python -m main --replies 1728108619189874825
        """,
    )

    parser.add_argument(
        "queries",
        nargs="*",
        help="Query IDs to run (e.g., 1 2 3). Use --list to see available queries.",
    )
    parser.add_argument("--all", action="store_true", help="Run all available queries")
    parser.add_argument(
        "--type",
        choices=registry.types(),
        help="Run all queries of a specific type (topic, profile, replies)",
    )
    parser.add_argument("--list", action="store_true", help="List all available queries and exit")
    parser.add_argument(
        "--list-types", action="store_true", help="List all available query types and exit"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the REST API server (FastAPI with Swagger docs at /docs)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="API server port (default: 8002)",
    )

    parser.add_argument("--topic", metavar="KEYWORD", help="Create a custom topic/keyword search")
    parser.add_argument(
        "--profile",
        metavar="USERNAME",
        help="Create a custom profile search (username without @)",
    )
    parser.add_argument(
        "--replies",
        metavar="CONVERSATION_ID",
        help="Create a custom replies search for a conversation ID",
    )

    parser.add_argument(
        "--max-items",
        type=int,
        default=100,
        help="Maximum number of items to fetch (default: 100)",
    )
    parser.add_argument(
        "--sort",
        choices=["Latest", "Top"],
        default="Latest",
        help="Sort order for topic searches (default: Latest)",
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        help="Start date for profile searches (format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--until",
        metavar="YYYY-MM-DD",
        help="End date for profile searches (format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--only-verified",
        action="store_true",
        help="Only fetch tweets from verified users (topic searches)",
    )
    parser.add_argument(
        "--only-image",
        action="store_true",
        help="Only fetch tweets with images (topic searches)",
    )
    parser.add_argument("--lang", default="en", help="Tweet language (default: en)")
    parser.add_argument(
        "--output-format",
        choices=["min", "max"],
        default="min",
        help=(
            "Output JSON format: min keeps only id/url/text/fullText/author plus "
            "retweetCount/replyCount/likeCount/quoteCount/viewCount/createdAt (default: min)"
        ),
    )
    parser.add_argument(
        "--actor-name",
        default=None,
        help="Apify actor name to run (default: from APIFY_ACTOR_NAME env or config).",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    registry = build_default_registry()
    parser = build_parser(registry)
    args = parser.parse_args(argv)

    # Start API server if requested
    if args.serve:
        import uvicorn
        from mcp_twitter.app import create_app
        from mcp_twitter.logging_config import get_logging_config
        
        print(f"🚀 Starting Twitter Scraper API server...")
        print(f"   Swagger docs: http://{args.host}:{args.port}/docs")
        print(f"   ReDoc: http://{args.host}:{args.port}/redoc")
        print(f"   API root: http://{args.host}:{args.port}/")
        print(f"\n   Press CTRL+C to stop\n")
        
        uvicorn.run(
            "mcp_twitter.app:create_app",
            host=args.host,
            port=args.port,
            log_config=get_logging_config(),
            factory=True,
        )
        return 0

    if args.list_types:
        _print_types(registry)
        return 0

    if args.list:
        _print_queries(registry, query_type=args.type)
        return 0

    queries_to_run: list[QueryDefinition] = []

    if args.topic:
        queries_to_run.append(
            create_topic_query(
                args.topic,
                max_items=args.max_items,
                sort=args.sort,
                only_verified=args.only_verified,
                only_image=args.only_image,
                lang=args.lang,
            )
        )
    if args.profile:
        queries_to_run.append(
            create_profile_query(
                args.profile,
                max_items=args.max_items,
                since=args.since,
                until=args.until,
                lang=args.lang,
            )
        )
    if args.replies:
        queries_to_run.append(
            create_replies_query(
                args.replies,
                max_items=args.max_items,
                lang=args.lang,
            )
        )

    if not queries_to_run:
        if args.all:
            queries_to_run = registry.list_queries()
        elif args.type:
            queries_to_run = registry.by_type(args.type)
        elif args.queries:
            for qid in args.queries:
                q = registry.get(qid)
                if not q:
                    print(f"❌ Warning: Query '{qid}' not found. Skipping.")
                    continue
                queries_to_run.append(q)

    if not queries_to_run:
        parser.print_help()
        print("\n")
        _print_types(registry)
        print("\n")
        _print_queries(registry)
        print(
            "\n💡 Tip: Use --type <type> to run queries by type, or create custom queries with "
            "--topic, --profile, or --replies"
        )
        return 0

    try:
        token = _load_apify_token()
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return 1

    scraper = TwitterScraper(
        apify_token=token,
        results_dir=Path("results"),
        actor_name=args.actor_name,  # Use config default if None
        output_format=args.output_format,  # type: ignore[arg-type]
    )
    _run_queries(scraper, queries_to_run)
    return 0


