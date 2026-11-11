from django.core.management.base import BaseCommand

from interests.services.news.ingestion import (
    NewsIngestionService,
)

from interests.services.news.matching import (
    NewsMatchingService,
)


class Command(BaseCommand):

    help = "Collect news and match articles to user interests"

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.NOTICE(
                "Starting DailyPulse AI news collection..."
            )
        )

        # Step 1: Collect articles.
        ingestion = NewsIngestionService()

        result = ingestion.collect()

        self.stdout.write(
            self.style.SUCCESS(
                f"Queries processed: {result['queries_processed']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Articles saved: {result['articles_saved']}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"Duplicates skipped: {result['duplicates']}"
            )
        )

        if result["errors"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Collection errors: {len(result['errors'])}"
                )
            )

        # Step 2: Match articles with users.
        matcher = NewsMatchingService()

        matching_result = matcher.match_articles()

        self.stdout.write(
            self.style.SUCCESS(
                f"User article matches created: "
                f"{matching_result['total_matches']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "DailyPulse AI news collection completed."
            )
        )