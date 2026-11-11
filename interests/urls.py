from django.urls import path
from . import views

urlpatterns = [
    # Interest management
    path("", views.interest_list, name="interest_list"),
    path("create/", views.interest_create, name="interest_create"),
    path("<int:pk>/edit/", views.interest_edit, name="interest_edit"),
    path("<int:pk>/delete/", views.interest_delete, name="interest_delete"),
    path("<int:pk>/toggle/", views.toggle_interest, name="toggle_interest"),

    # Tag management
    path("<int:pk>/tags/add/", views.add_tag, name="add_tag"),
    path("<int:pk>/tags/<int:tag_id>/edit/", views.edit_tag, name="edit_tag"),
    path("<int:pk>/tags/<int:tag_id>/remove/", views.remove_tag, name="remove_tag"),

    # AI tag generation
    path("<int:pk>/generate-tags/", views.generate_tags, name="generate_tags"),

    # Personalized news feed
    path("news/", views.news_feed, name="news_feed"),
    path(
        "news/<int:article_id>/toggle-read/",
        views.toggle_article_read,
        name="toggle_article_read",
    ),
]