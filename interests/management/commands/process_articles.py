
import logging

from django.core.management.base import BaseCommand, CommandError

from interests.models import Article
from interests.services.ai.article_intelligence_service import (
    ArticleIntelligenceService,
)


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Generate AI summaries and intelligence for collected news articles."

    def add_arguments(self, parser):

        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of articles to process (default: 10).",
        )

        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Also retry articles whose previous AI processing failed.",
        )

        parser.add_argument(
            "--article-id",
            type=int,
            help="Process one specific article by its database ID.",
        )

    def handle(self, *args, **options):

        limit = options["limit"]
        retry_failed = options["retry_failed"]
        article_id = options["article_id"]

        if limit < 1:
            raise CommandError("--limit must be at least 1.")

        # Select articles eligible for AI processing.
        eligible_statuses = [Article.AIStatus.PENDING]

        if retry_failed:
            eligible_statuses.append(Article.AIStatus.FAILED)

        queryset = Article.objects.filter(
            ai_status__in=eligible_statuses
        ).order_by("fetched_at")

        if article_id is not None:
            queryset = Article.objects.filter(
                id=article_id,
                ai_status__in=eligible_statuses
            )

        articles = list(queryset[:limit])

        if not articles:
            self.stdout.write(
                self.style.WARNING(
                    "No eligible articles found for AI processing."
                )
            )
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Starting AI processing for {len(articles)} article(s)..."
            )
        )

        service = ArticleIntelligenceService()

        processed = 0
        succeeded = 0
        failed = 0

        for article in articles:

            processed += 1

            self.stdout.write(
                f"\n[{processed}/{len(articles)}] "
                f"Processing Article ID: {article.id}"
            )

            self.stdout.write(
                f"Title: {article.title[:100]}"
            )

            try:

                result = service.analyze_article(article)

                if result is None:
                    self.stdout.write(
                        self.style.WARNING(
                            "Article was skipped."
                        )
                    )
                    continue

                succeeded += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        "AI analysis completed successfully."
                    )
                )

                self.stdout.write(
                    f"Category: {article.ai_category}"
                )

                self.stdout.write(
                    f"Importance: {article.ai_importance_score}/100"
                )

                self.stdout.write(
                    f"Keywords: {', '.join(article.ai_keywords)}"
                )

            except Exception as exc:

                failed += 1

                logger.exception(
                    "AI processing failed for article ID %s",
                    article.id
                )

                self.stdout.write(
                    self.style.ERROR(
                        f"AI processing failed: {str(exc)[:300]}"
                    )
                )

        self.stdout.write("\n" + "=" * 50)

        self.stdout.write("AI PROCESSING SUMMARY")
        self.stdout.write("=" * 50)

        self.stdout.write(f"Articles processed: {processed}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully analyzed: {succeeded}"
            )
        )

        if failed:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed: {failed}"
                )
            )
        else:
            self.stdout.write("Failed: 0")

        self.stdout.write("=" * 50)
