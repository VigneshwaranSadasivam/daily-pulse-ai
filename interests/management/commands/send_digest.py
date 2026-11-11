
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import UserPreference
from interests.models import DigestDelivery
from interests.services.digest.digest_service import DigestService


User = get_user_model()


class Command(BaseCommand):

    help = "Preview or send a personalized DailyPulse AI digest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address of the digest recipient.",
        )

        parser.add_argument(
            "--send",
            action="store_true",
            help="Actually send the email.",
        )

    def get_period_key(self, frequency, user_timezone):
        """
        Generate a daily or weekly period key
        using the user's configured timezone.
        """

        local_now = timezone.localtime(
            timezone.now(),
            user_timezone,
        )

        if frequency == UserPreference.Frequency.WEEKLY:
            iso = local_now.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"

        return local_now.strftime("%Y-%m-%d")

    def handle(self, *args, **options):

        email = options["email"].strip()
        should_send = options["send"]

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(
                f"No user found with email: {email}"
            )

        service = DigestService()
        digest = service.get_user_digest(user)

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
                    "No new articles available for this digest."
                )
            )
            return

        preference = digest["preference"]

        frequency = (
            preference.frequency
            if preference
            else UserPreference.Frequency.DAILY
        )

        timezone_name = (
            preference.timezone
            if preference
            else settings.TIME_ZONE
        )

        try:
            user_timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            raise CommandError(
                f"Invalid timezone configured for user: {timezone_name}"
            )

        period_key = self.get_period_key(
            frequency,
            user_timezone,
        )

        subject = (
            "Your DailyPulse AI News Digest"
            if frequency == UserPreference.Frequency.DAILY
            else "Your DailyPulse AI Weekly News Digest"
        )

        context = {
            "user": user,
            "articles": articles,
            "total_articles": len(articles),
        }

        text_content = render_to_string(
            "interests/emails/daily_digest.txt",
            context,
        )

        html_content = render_to_string(
            "interests/emails/daily_digest.html",
            context,
        )

        self.stdout.write("")
        self.stdout.write("=" * 65)
        self.stdout.write(
            self.style.SUCCESS("DAILYPULSE AI EMAIL")
        )
        self.stdout.write("=" * 65)

        self.stdout.write(f"Recipient: {user.email}")
        self.stdout.write(f"Frequency: {frequency}")
        self.stdout.write(f"Period: {period_key}")
        self.stdout.write(f"Articles: {len(articles)}")

        # Preview mode does not create a delivery record.
        if not should_send:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW MODE - No email was sent."
                )
            )
            self.stdout.write("")
            self.stdout.write(text_content)
            return

        # Create or retrieve the delivery record.
        with transaction.atomic():

            delivery, created = (
                DigestDelivery.objects.get_or_create(
                    user=user,
                    frequency=frequency,
                    period_key=period_key,
                    defaults={
                        "status": DigestDelivery.Status.PENDING,
                    },
                )
            )

            if not created:

                if delivery.status == DigestDelivery.Status.SENT:
                    self.stdout.write(
                        self.style.WARNING(
                            "Digest already sent for this period. Skipping."
                        )
                    )
                    return

                if delivery.status == DigestDelivery.Status.PENDING:
                    self.stdout.write(
                        self.style.WARNING(
                            "A digest delivery is already pending "
                            "for this period. Skipping."
                        )
                    )
                    return

                # Retry a previously failed delivery.
                if delivery.status == DigestDelivery.Status.FAILED:
                    delivery.status = DigestDelivery.Status.PENDING
                    delivery.error = ""
                    delivery.sent_at = None
                    delivery.article_count = 0
                    delivery.save(
                        update_fields=[
                            "status",
                            "error",
                            "sent_at",
                            "article_count",
                            "updated_at",
                        ]
                    )
                    delivery.articles.clear()

            # Store the exact articles selected for this digest.
            article_ids = [
                item["article"].id
                for item in articles
            ]

            delivery.articles.set(article_ids)
            delivery.article_count = len(article_ids)
            delivery.save(
                update_fields=[
                    "article_count",
                    "updated_at",
                ]
            )

        # Send outside the database transaction.
        try:

            message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

            message.attach_alternative(
                html_content,
                "text/html",
            )

            sent_count = message.send(
                fail_silently=False
            )

            if sent_count != 1:
                raise RuntimeError(
                    "Email backend did not confirm delivery."
                )

            delivery.status = DigestDelivery.Status.SENT
            delivery.sent_at = timezone.now()
            delivery.error = ""

            delivery.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "error",
                    "updated_at",
                ]
            )

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Digest successfully processed for {user.email}."
                )
            )

            self.stdout.write(
                f"Delivery ID: {delivery.id}"
            )

            self.stdout.write(
                f"Articles delivered: {delivery.article_count}"
            )

        except Exception as exc:

            delivery.status = DigestDelivery.Status.FAILED
            delivery.error = str(exc)

            delivery.save(
                update_fields=[
                    "status",
                    "error",
                    "updated_at",
                ]
            )

            self.stderr.write(
                self.style.ERROR(
                    f"Digest delivery failed: {exc}"
                )
            )

            raise CommandError(
                "Digest email delivery failed."
            ) from exc
