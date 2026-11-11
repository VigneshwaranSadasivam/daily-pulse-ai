import logging

from django.db import transaction

from interests.models import (
    Article,
    ArticleTag,
    Interest,
    InterestTag,
    UserArticle,
)

from .common import normalize_text


logger = logging.getLogger(__name__)


class NewsMatchingService:

    def calculate_relevance(
        self,
        article,
        interest,
        tags
    ):

        title = normalize_text(article.title)

        description = normalize_text(
            article.description
        )

        searchable_text = f"{title} {description}"

        matched_tags = []
        score = 0

        # Parent interest match.
        interest_name = normalize_text(
            interest.name
        )

        if interest_name in searchable_text:
            score += 40

        # Tag matching.
        for tag in tags:

            keyword = normalize_text(tag.name)

            if not keyword:
                continue

            if keyword in searchable_text:

                matched_tags.append(tag.name)

                score += 20

                ArticleTag.objects.get_or_create(
                    article=article,
                    tag=tag,
                    defaults={
                        "matched_keyword": tag.name
                    }
                )

        # Avoid scores greater than 100.
        score = min(score, 100)

        return score, matched_tags

    def match_articles(self):

        total_matches = 0

        interests = (
            Interest.objects
            .filter(
                user__is_active=True,
                is_active=True,
            )
            .prefetch_related("interest_tags__tag")
        )

        articles = Article.objects.all()

        for interest in interests:

            tags = [
                relation.tag
                for relation in interest.interest_tags.all()
                if relation.tag.is_active
            ]

            for article in articles.iterator():

                score, matched_tags = (
                    self.calculate_relevance(
                        article,
                        interest,
                        tags
                    )
                )

                if score < 20:
                    continue

                with transaction.atomic():

                    user_article, created = (
                        UserArticle.objects.get_or_create(
                            user=interest.user,
                            article=article,
                            interest=interest,
                            defaults={
                                "relevance_score": score,
                                "matched_tags": matched_tags,
                            }
                        )
                    )

                    if created:
                        total_matches += 1

                    else:
                        # Refresh score and matched tags
                        # without changing the user's read status.
                        user_article.relevance_score = score
                        user_article.matched_tags = matched_tags

                        user_article.save(
                            update_fields=[
                                "relevance_score",
                                "matched_tags",
                            ]
                        )

        return {
            "total_matches": total_matches
        }