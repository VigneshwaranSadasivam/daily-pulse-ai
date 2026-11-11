
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from interests.services.digest.digest_service import DigestService


User = get_user_model()


class Command(BaseCommand):

    help = "Preview a personalized news digest for a user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address of the user.",
        )

    def handle(self, *args, **options):

        email = options["email"].strip()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(
                f"No user found with email: {email}"
            )

        service = DigestService()
        digest = service.get_user_digest(user)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("=" * 65)
        )
        self.stdout.write(
            self.style.SUCCESS("DAILYPULSE AI - DIGEST PREVIEW")
        )
        self.stdout.write(
            self.style.SUCCESS("=" * 65)
        )

        self.stdout.write(f"User: {user.email}")
        self.stdout.write(
            f"Account active: {user.is_active}"
        )

        preference = digest["preference"]

        if preference:
            self.stdout.write(
                f"Frequency: {preference.get_frequency_display()}"
            )
            self.stdout.write(
                f"Delivery time: {preference.delivery_time}"
            )
            self.stdout.write(
                f"Timezone: {preference.timezone}"
            )
            self.stdout.write(
                f"Maximum articles: {preference.max_articles}"
            )
            self.stdout.write(
                f"Paused: {preference.is_paused}"
            )
        else:
            self.stdout.write(
                "Preferences: Default settings"
            )

        self.stdout.write("")

        if not digest["eligible"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Digest skipped: {digest['reason']}"
                )
            )
            return

        articles = digest["articles"]

        if not articles:
            self.stdout.write(
                self.style.WARNING(
                    "No matching articles found for this digest period."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Articles selected: {digest['total_articles']}"
            )
        )

        self.stdout.write("-" * 65)

        for index, item in enumerate(articles, start=1):

            article = item["article"]

            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\n{index}. {article.title}"
                )
            )

            self.stdout.write(
                f"Category: {article.ai_category or 'Uncategorized'}"
            )

            self.stdout.write(
                f"Relevance: {item['relevance_score']}/100"
            )

            self.stdout.write(
                f"AI importance: {item['importance_score']}/100"
            )

            self.stdout.write(
                "Interests: "
                + (
                    ", ".join(item["interests"])
                    or "None"
                )
            )

            self.stdout.write(
                "Matched tags: "
                + (
                    ", ".join(item["matched_tags"])
                    or "None"
                )
            )

            self.stdout.write(
                f"URL: {article.url}"
            )

            self.stdout.write(
                f"Summary: {item['summary'][:400]}"
            )

            self.stdout.write("-" * 65)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Digest preview completed. No email was sent."
            )
        )
