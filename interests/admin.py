from django.contrib import admin

from .models import (
    Interest,
    Tag,
    InterestTag,
    NewsSource,
    Article,
    ArticleTag,
    UserArticle,
)


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "user",
        "is_active",
        "created_at",
    )

    list_filter = ("is_active",)
    search_fields = ("name", "user__email")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "user",
        "source",
        "is_active",
    )

    list_filter = ("source", "is_active")
    search_fields = ("name", "user__email")


admin.site.register(InterestTag)


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "source_type",
        "is_active",
    )


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "source",
        "published_at",
        "fetched_at",
    )

    search_fields = ("title", "url")
    list_filter = ("source",)


@admin.register(ArticleTag)
class ArticleTagAdmin(admin.ModelAdmin):

    list_display = (
        "article",
        "tag",
        "matched_keyword",
    )


@admin.register(UserArticle)
class UserArticleAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "interest",
        "article",
        "relevance_score",
        "is_read",
    )

    list_filter = ("is_read", "interest")
    search_fields = (
        "user__email",
        "article__title",
    )