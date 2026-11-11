from django.conf import settings
from django.db import models


class Interest(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interests"
    )

    name = models.CharField(max_length=150)

    normalized_name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "normalized_name"],
                name="unique_user_interest"
            )
        ]

    def save(self, *args, **kwargs):
        self.normalized_name = " ".join(
            self.name.casefold().split()
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Tag(models.Model):

    class Source(models.TextChoices):
        AI = "ai", "AI Generated"
        MANUAL = "manual", "Manual"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags"
    )

    name = models.CharField(max_length=150)

    normalized_name = models.CharField(max_length=150)

    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.MANUAL
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "normalized_name"],
                name="unique_user_tag"
            )
        ]

    def save(self, *args, **kwargs):
        self.normalized_name = " ".join(
            self.name.casefold().split()
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class InterestTag(models.Model):

    interest = models.ForeignKey(
        Interest,
        on_delete=models.CASCADE,
        related_name="interest_tags"
    )

    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="interest_tags"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["interest", "tag"],
                name="unique_interest_tag"
            )
        ]

    def __str__(self):
        return f"{self.interest.name} - {self.tag.name}"

class NewsSource(models.Model):

    class SourceType(models.TextChoices):
        RSS = "rss", "RSS Feed"
        API = "api", "API"

    name = models.CharField(max_length=100)

    source_type = models.CharField(
        max_length=10,
        choices=SourceType.choices
    )

    base_url = models.URLField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name



class Article(models.Model):

    class AIStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        NewsSource,
        on_delete=models.SET_NULL,
        null=True,
        related_name="articles"
    )

    title = models.CharField(max_length=500)

    description = models.TextField(blank=True)

    url = models.URLField(max_length=2000, unique=True)

    author = models.CharField(max_length=255, blank=True)

    published_at = models.DateTimeField(
        null=True,
        blank=True
    )

    content_hash = models.CharField(
        max_length=64,
        unique=True
    )

    external_id = models.CharField(
        max_length=255,
        blank=True
    )

    fetched_at = models.DateTimeField(auto_now_add=True)

    # AI Intelligence fields

    ai_summary = models.TextField(
        blank=True,
        default=""
    )

    ai_category = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    ai_keywords = models.JSONField(
        default=list,
        blank=True
    )

    ai_importance_score = models.PositiveSmallIntegerField(
        default=0
    )

    ai_status = models.CharField(
        max_length=20,
        choices=AIStatus.choices,
        default=AIStatus.PENDING,
        db_index=True
    )

    ai_model = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    ai_analyzed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    ai_error = models.TextField(
        blank=True,
        default=""
    )

    class Meta:
        ordering = ["-published_at", "-fetched_at"]

    def __str__(self):
        return self.title

class ArticleTag(models.Model):

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="article_tags"
    )

    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="article_tags"
    )

    matched_keyword = models.CharField(
        max_length=150,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "tag"],
                name="unique_article_tag"
            )
        ]


class UserArticle(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="news_articles"
    )

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="user_articles"
    )

    interest = models.ForeignKey(
        Interest,
        on_delete=models.CASCADE,
        related_name="user_articles"
    )

    relevance_score = models.PositiveSmallIntegerField(
        default=0
    )

    matched_tags = models.JSONField(default=list)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article", "interest"],
                name="unique_user_article_interest"
            )
        ]

        ordering = ["-relevance_score", "-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.article.title}"


class DigestDelivery(models.Model):

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="digest_deliveries",
    )

    frequency = models.CharField(
        max_length=10,
        choices=Frequency.choices,
    )

    # Examples: 2026-11-11 (daily), 2026-W46 (weekly)
    period_key = models.CharField(max_length=20)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    articles = models.ManyToManyField(
        "Article",
        related_name="digest_deliveries",
        blank=True,
    )

    article_count = models.PositiveIntegerField(default=0)

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "frequency", "period_key"],
                name="unique_user_digest_period",
            )
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.frequency} - "
            f"{self.period_key} - "
            f"{self.status}"
        )
