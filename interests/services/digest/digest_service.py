
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from accounts.models import UserPreference
from interests.models import UserArticle, DigestDelivery


class DigestService:

    DEFAULT_MAX_ARTICLES = 10

    def get_user_preferences(self, user):
        """
        Return the user's preferences.

        If the user has no preference record,
        use the model's default values.
        """

        try:
            return user.preferences
        except UserPreference.DoesNotExist:
            return None

    def get_digest_period(self, frequency):
        """
        Return the time window for the digest.
        """

        if frequency == UserPreference.Frequency.WEEKLY:
            return timedelta(days=7)

        return timedelta(days=1)

    def get_user_digest(self, user):
        """
        Build a personalized digest for one user.

        Returns:
            {
                "eligible": bool,
                "reason": str,
                "user": User,
                "preference": UserPreference or None,
                "articles": list,
                "total_articles": int,
            }
        """

        preference = self.get_user_preferences(user)

        # Skip inactive users.
        if not user.is_active:
            return self._empty_result(
                user,
                preference,
                "User account is inactive.",
            )

        # Skip paused digests.
        if preference and preference.is_paused:
            return self._empty_result(
                user,
                preference,
                "Digest delivery is paused.",
            )

        frequency = (
            preference.frequency
            if preference
            else UserPreference.Frequency.DAILY
        )

        max_articles = (
            preference.max_articles
            if preference
            else self.DEFAULT_MAX_ARTICLES
        )

        if max_articles <= 0:
            return self._empty_result(
                user,
                preference,
                "Maximum article count is zero.",
            )

        # Determine the digest time window.
        now = timezone.now()
        cutoff = now - self.get_digest_period(frequency)

        # Find articles that have already been successfully
        # delivered to this user.
        sent_article_ids = (
            DigestDelivery.objects
            .filter(
                user=user,
                status=DigestDelivery.Status.SENT,
                articles__isnull=False,
            )
            .values_list("articles__id", flat=True)
        )

        # Fetch only articles matched to this user
        # during the selected digest period.
        matches = (
            UserArticle.objects
            .filter(
                user=user,
                created_at__gte=cutoff,
            )
            .exclude(
                article_id__in=sent_article_ids,
            )
            .select_related(
                "article",
                "article__source",
                "interest",
            )
            .order_by(
                "-relevance_score",
                "-article__ai_importance_score",
                "-created_at",
            )
        )

        # Group multiple interest matches into one article.
        grouped_articles = {}

        for match in matches:

            article = match.article
            article_id = article.id

            if article_id not in grouped_articles:

                grouped_articles[article_id] = {
                    "article": article,
                    "relevance_score": match.relevance_score,
                    "importance_score": article.ai_importance_score,
                    "interests": set(),
                    "matched_tags": set(),
                }

            item = grouped_articles[article_id]

            item["interests"].add(match.interest.name)

            for tag in (match.matched_tags or []):
                if isinstance(tag, str):
                    item["matched_tags"].add(tag)

            item["relevance_score"] = max(
                item["relevance_score"],
                match.relevance_score,
            )

        # Sort by relevance first, then AI importance.
        digest_articles = sorted(
            grouped_articles.values(),
            key=lambda item: (
                item["relevance_score"],
                item["importance_score"],
            ),
            reverse=True,
        )

        # Limit the number of articles.
        digest_articles = digest_articles[:max_articles]

        # Prepare clean data for the email template.
        for item in digest_articles:

            item["interests"] = sorted(item["interests"])
            item["matched_tags"] = sorted(item["matched_tags"])

            article = item["article"]

            ai_summary = (article.ai_summary or "").strip()
            description = (article.description or "").strip()

            # Avoid displaying an AI summary that only repeats the title.
            if ai_summary.casefold() == article.title.strip().casefold():
                ai_summary = ""

            # Prefer the AI summary when it contains useful information.
            if len(ai_summary) >= 80:
                item["summary"] = ai_summary

            elif len(description) >= 80:
                item["summary"] = description

            elif ai_summary:
                item["summary"] = ai_summary

            elif description:
                item["summary"] = description

            else:
                item["summary"] = "Open the article to read the full story."

        return {
            "eligible": True,
            "reason": "Digest generated successfully.",
            "user": user,
            "preference": preference,
            "frequency": frequency,
            "articles": digest_articles,
            "total_articles": len(digest_articles),
        }

    def _empty_result(self, user, preference, reason):
        return {
            "eligible": False,
            "reason": reason,
            "user": user,
            "preference": preference,
            "frequency": None,
            "articles": [],
            "total_articles": 0,
        }
