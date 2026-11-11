import logging
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .forms import InterestForm, TagForm
from .models import Interest, Tag, InterestTag
from .services.gemini_service import GeminiService

from django.core.paginator import Paginator
from django.db.models import Prefetch, Q

from .models import Interest, Tag, InterestTag, Article, UserArticle


logger = logging.getLogger(__name__)


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def normalize_name(name):
    return " ".join(name.casefold().split())


def get_user_interest(request, pk):
    return get_object_or_404(
        Interest,
        pk=pk,
        user=request.user,
    )


def get_user_tag(request, tag_id):
    return get_object_or_404(
        Tag,
        pk=tag_id,
        user=request.user,
    )


# --------------------------------------------------
# Interest list
# --------------------------------------------------

@login_required
def interest_list(request):

    interests = (
        Interest.objects
        .filter(user=request.user)
        .prefetch_related("interest_tags__tag")
        .order_by("-created_at")
    )

    context = {
        "interests": interests,
        "tag_form": TagForm(),
    }

    return render(
        request,
        "interests/interest_list.html",
        context,
    )


# --------------------------------------------------
# Create interest
# --------------------------------------------------

@login_required
def interest_create(request):

    if request.method == "POST":
        form = InterestForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            interest = form.save(commit=False)
            interest.user = request.user

            try:
                interest.save()
            except IntegrityError:
                form.add_error(
                    "name",
                    "You already have this interest.",
                )
            else:
                messages.success(
                    request,
                    "Interest created successfully.",
                )
                return redirect("interest_list")
    else:
        form = InterestForm(user=request.user)

    return render(
        request,
        "interests/interest_form.html",
        {
            "form": form,
            "page_title": "Add Interest",
        },
    )


# --------------------------------------------------
# Edit interest
# --------------------------------------------------

@login_required
def interest_edit(request, pk):

    interest = get_user_interest(request, pk)

    if request.method == "POST":
        form = InterestForm(
            request.POST,
            instance=interest,
            user=request.user,
        )

        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                form.add_error(
                    "name",
                    "You already have this interest.",
                )
            else:
                messages.success(
                    request,
                    "Interest updated successfully.",
                )
                return redirect("interest_list")
    else:
        form = InterestForm(
            instance=interest,
            user=request.user,
        )

    return render(
        request,
        "interests/interest_form.html",
        {
            "form": form,
            "page_title": "Edit Interest",
        },
    )


# --------------------------------------------------
# Delete interest
# --------------------------------------------------

@login_required
@require_POST
def interest_delete(request, pk):

    interest = get_user_interest(request, pk)

    interest.delete()

    messages.success(
        request,
        "Interest deleted successfully.",
    )

    return redirect("interest_list")


# --------------------------------------------------
# Enable / Disable interest
# --------------------------------------------------

@login_required
@require_POST
def toggle_interest(request, pk):

    interest = get_user_interest(request, pk)

    interest.is_active = not interest.is_active

    interest.save(update_fields=[
        "is_active",
        "updated_at",
    ])

    status = (
        "enabled"
        if interest.is_active
        else "disabled"
    )

    messages.success(
        request,
        f"{interest.name} {status} successfully.",
    )

    return redirect("interest_list")


# --------------------------------------------------
# Add custom tag
# --------------------------------------------------

@login_required
@require_POST
def add_tag(request, pk):

    interest = get_user_interest(request, pk)

    form = TagForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Please enter a valid tag name.",
        )
        return redirect("interest_list")

    name = form.cleaned_data["name"]
    normalized = normalize_name(name)

    with transaction.atomic():

        tag, _ = Tag.objects.get_or_create(
            user=request.user,
            normalized_name=normalized,
            defaults={
                "name": name,
                "source": Tag.Source.MANUAL,
                "is_active": True,
            },
        )

        if not tag.is_active:
            tag.is_active = True
            tag.save(update_fields=["is_active"])

        _, created = InterestTag.objects.get_or_create(
            interest=interest,
            tag=tag,
        )

    if created:
        messages.success(
            request,
            f"Tag '{name}' added successfully.",
        )
    else:
        messages.info(
            request,
            f"Tag '{name}' already exists in this interest.",
        )

    return redirect("interest_list")


# --------------------------------------------------
# Remove tag from interest
# --------------------------------------------------

@login_required
@require_POST
def remove_tag(request, pk, tag_id):

    interest = get_user_interest(request, pk)

    relation = get_object_or_404(
        InterestTag,
        interest=interest,
        tag_id=tag_id,
        tag__user=request.user,
    )

    tag_name = relation.tag.name

    relation.delete()

    messages.success(
        request,
        f"Tag '{tag_name}' removed from this interest.",
    )

    # The Tag record is retained because it may
    # be used by another interest.

    return redirect("interest_list")


# --------------------------------------------------
# Edit tag
# --------------------------------------------------

@login_required
@require_POST
def edit_tag(request, pk, tag_id):

    interest = get_user_interest(request, pk)
    tag = get_user_tag(request, tag_id)

    get_object_or_404(
        InterestTag,
        interest=interest,
        tag=tag,
    )

    form = TagForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Please enter a valid tag name.",
        )
        return redirect("interest_list")

    new_name = form.cleaned_data["name"]
    normalized = normalize_name(new_name)

    # A tag can be shared across several interests.
    # If shared, clone it rather than renaming it
    # everywhere without the user's permission.

    with transaction.atomic():

        if tag.normalized_name == normalized:
            tag.name = new_name
            tag.save(update_fields=["name"])

        else:
            existing = Tag.objects.filter(
                user=request.user,
                normalized_name=normalized,
            ).first()

            if existing:
                InterestTag.objects.get_or_create(
                    interest=interest,
                    tag=existing,
                )

                InterestTag.objects.filter(
                    interest=interest,
                    tag=tag,
                ).delete()

            else:
                relation_count = (
                    InterestTag.objects
                    .filter(tag=tag)
                    .count()
                )

                if relation_count > 1:
                    new_tag = Tag.objects.create(
                        user=request.user,
                        name=new_name,
                        normalized_name=normalized,
                        source=Tag.Source.MANUAL,
                    )

                    InterestTag.objects.get_or_create(
                        interest=interest,
                        tag=new_tag,
                    )

                    InterestTag.objects.filter(
                        interest=interest,
                        tag=tag,
                    ).delete()

                else:
                    tag.name = new_name
                    tag.normalized_name = normalized
                    tag.source = Tag.Source.MANUAL
                    tag.save(update_fields=[
                        "name",
                        "normalized_name",
                        "source",
                    ])

    messages.success(
        request,
        "Tag updated successfully.",
    )

    return redirect("interest_list")


# --------------------------------------------------
# Gemini AI tag generation
# --------------------------------------------------

@login_required
@require_POST
def generate_tags(request, pk):

    interest = get_user_interest(request, pk)

    start_time = time.monotonic()

    try:
        service = GeminiService()

        # Uses your existing working Gemini integration.
        suggestions = service.generate_tags(
            interest.name,
            interest.description,
        )

        created_count = 0

        with transaction.atomic():

            for name in suggestions:

                if not isinstance(name, str):
                    continue

                name = " ".join(name.strip().split())

                if not name or len(name) > 150:
                    continue

                normalized = normalize_name(name)

                tag, _ = Tag.objects.get_or_create(
                    user=request.user,
                    normalized_name=normalized,
                    defaults={
                        "name": name,
                        "source": Tag.Source.AI,
                    },
                )

                _, created = (
                    InterestTag.objects.get_or_create(
                        interest=interest,
                        tag=tag,
                    )
                )

                if created:
                    created_count += 1

        elapsed = time.monotonic() - start_time

        logger.info(
            "AI tag generation completed in %.2fs. "
            "User ID: %s, Interest ID: %s",
            elapsed,
            request.user.pk,
            interest.pk,
        )

        if created_count:
            messages.success(
                request,
                f"{created_count} AI tags added successfully.",
            )
        else:
            messages.info(
                request,
                "No new tags found. Existing tags were preserved.",
            )

    except Exception:
        logger.exception(
            "AI tag generation failed for interest ID %s",
            interest.pk,
        )

        messages.error(
            request,
            "AI tag generation is temporarily unavailable. "
            "Please try again later.",
        )

    return redirect("interest_list")

# --------------------------------------------------
# Personalized News Feed
# --------------------------------------------------

@login_required
def news_feed(request):

    # Get only articles matched to the logged-in user.
    # Prefetch all matches for each article so duplicate
    # matches across interests don't create duplicate cards.

    user_matches = (
        UserArticle.objects
        .filter(user=request.user)
        .select_related("interest")
        .order_by("-relevance_score", "-created_at")
    )

    articles = (
        Article.objects
        .filter(user_articles__user=request.user)
        .select_related("source")
        .distinct()
        .prefetch_related(
            Prefetch(
                "user_articles",
                queryset=user_matches,
                to_attr="current_user_matches",
            )
        )
        .order_by(
            "-ai_importance_score",
            "-published_at",
            "-fetched_at",
        )
    )

    # Available categories for this user's feed.
    categories = (
        Article.objects
        .filter(user_articles__user=request.user)
        .exclude(ai_category="")
        .values_list("ai_category", flat=True)
        .distinct()
        .order_by("ai_category")
    )

    selected_category = request.GET.get("category", "").strip()
    selected_status = request.GET.get("status", "all").strip()
    search_query = request.GET.get("q", "").strip()

    # Category filter.
    if selected_category:
        articles = articles.filter(
            ai_category__iexact=selected_category
        )

    # Search filter.
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(ai_summary__icontains=search_query)
            | Q(ai_category__icontains=search_query)
        )

    # Convert article matches into one card per article.
    feed_articles = []

    for article in articles:

        matches = article.current_user_matches

        if not matches:
            continue

        article.matching_interests = sorted({
            match.interest.name
            for match in matches
        })

        article.matched_tags = sorted({
            tag
            for match in matches
            for tag in (match.matched_tags or [])
        })

        article.is_read = all(
            match.is_read for match in matches
        )

        article.user_relevance = max(
            match.relevance_score for match in matches
        )

        feed_articles.append(article)

    # Read/unread filter.
    if selected_status == "unread":
        feed_articles = [
            article for article in feed_articles
            if not article.is_read
        ]

    elif selected_status == "read":
        feed_articles = [
            article for article in feed_articles
            if article.is_read
        ]

    # Counts for the current filtered feed.
    total_count = len(feed_articles)

    unread_count = sum(
        1 for article in feed_articles
        if not article.is_read
    )

    # Pagination.
    paginator = Paginator(feed_articles, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Preserve current filters when navigating pages.
    query_params = request.GET.copy()
    query_params.pop("page", None)
    filter_query = query_params.urlencode()

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "selected_category": selected_category,
        "selected_status": selected_status,
        "search_query": search_query,
        "total_count": total_count,
        "unread_count": unread_count,
        "filter_query": filter_query,
    }

    return render(
        request,
        "interests/news_feed.html",
        context,
    )


# --------------------------------------------------
# Mark article as read / unread
# --------------------------------------------------

@login_required
@require_POST
def toggle_article_read(request, article_id):

    matches = UserArticle.objects.filter(
        user=request.user,
        article_id=article_id,
    )

    if not matches.exists():
        get_object_or_404(
            UserArticle,
            user=request.user,
            article_id=article_id,
        )

    # If every matching row is read, mark all unread.
    # Otherwise, mark all as read.
    currently_read = not matches.filter(
        is_read=False
    ).exists()

    new_status = not currently_read

    matches.update(is_read=new_status)

    if new_status:
        messages.success(
            request,
            "Article marked as read.",
        )
    else:
        messages.success(
            request,
            "Article marked as unread.",
        )

    return redirect("news_feed")