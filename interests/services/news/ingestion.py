import logging

from django.db import IntegrityError, transaction

from interests.models import (
    Article,
    NewsSource,
    Interest,
    Tag,
)

from .google_news import GoogleNewsService
from .hacker_news import HackerNewsService
from .common import generate_content_hash


logger = logging.getLogger(__name__)


class NewsIngestionService:

    def __init__(self):

        self.google_news = GoogleNewsService()
        self.hacker_news = HackerNewsService()

    def get_sources(self):

        google, _ = NewsSource.objects.get_or_create(
            name="Google News",
            defaults={
                "source_type": NewsSource.SourceType.RSS,
                "base_url": (
                    "https://news.google.com/rss/search"
                ),
            }
        )

        hacker, _ = NewsSource.objects.get_or_create(
            name="Hacker News",
            defaults={
                "source_type": NewsSource.SourceType.API,
                "base_url": (
                    "https://hacker-news.firebaseio.com/v0"
                ),
            }
        )

        return google, hacker

    def get_search_queries(self):

        # Only use active interests and active tags.
        interests = Interest.objects.filter(
            user__is_active=True,
            is_active=True,
        ).prefetch_related("interest_tags__tag")

        queries = set()

        for interest in interests:

            queries.add(interest.name)

            for relation in interest.interest_tags.all():

                if relation.tag.is_active:
                    queries.add(relation.tag.name)

        # Prevent excessive RSS requests in the MVP.
        return sorted(queries, key=str.casefold)[:30]

    def save_articles(self, articles, source):

        saved_count = 0
        duplicate_count = 0

        for item in articles:

            title = item.get("title", "").strip()
            url = item.get("url", "").strip()

            if not title or not url:
                continue

            content_hash = generate_content_hash(
                title,
                url
            )

            try:

                with transaction.atomic():

                    article, created = Article.objects.get_or_create(
                        content_hash=content_hash,
                        defaults={
                            "source": source,
                            "title": title,
                            "description": item.get(
                                "description", ""
                            ),
                            "url": url,
                            "author": item.get("author", ""),
                            "published_at": item.get(
                                "published_at"
                            ),
                            "external_id": item.get(
                                "external_id", ""
                            ),
                        }
                    )

                    if created:
                        saved_count += 1
                    else:
                        duplicate_count += 1

            except IntegrityError:

                duplicate_count += 1

                logger.warning(
                    "Duplicate article encountered: %s",
                    url
                )

        return {
            "saved": saved_count,
            "duplicates": duplicate_count,
        }

    def collect(self):

        google_source, hacker_source = self.get_sources()

        total_saved = 0
        total_duplicates = 0
        errors = []

        # --------------------------------------
        # Google News
        # --------------------------------------

        queries = self.get_search_queries()

        for query in queries:

            try:

                articles = self.google_news.fetch_news(
                    query=query,
                    limit=15,
                )

                result = self.save_articles(
                    articles,
                    google_source,
                )

                total_saved += result["saved"]
                total_duplicates += result["duplicates"]

                logger.info(
                    "Google News query '%s': %s",
                    query,
                    result
                )

            except Exception as exc:

                logger.exception(
                    "Google News collection failed for %s",
                    query
                )

                errors.append(str(exc))

        # --------------------------------------
        # Hacker News
        # --------------------------------------

        try:

            articles = self.hacker_news.fetch_news(
                limit=30
            )

            result = self.save_articles(
                articles,
                hacker_source,
            )

            total_saved += result["saved"]
            total_duplicates += result["duplicates"]

        except Exception as exc:

            logger.exception(
                "Hacker News collection failed"
            )

            errors.append(str(exc))

        return {
            "queries_processed": len(queries),
            "articles_saved": total_saved,
            "duplicates": total_duplicates,
            "errors": errors,
        }