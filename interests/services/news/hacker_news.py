import logging
import requests

from datetime import datetime, timezone

from .common import clean_html, normalize_url


logger = logging.getLogger(__name__)


class HackerNewsService:

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "DailyPulseAI/1.0"
        })

    def fetch_news(self, limit=30):

        endpoint = f"{self.BASE_URL}/newstories.json"

        try:

            response = self.session.get(
                endpoint,
                timeout=15
            )

            response.raise_for_status()

            story_ids = response.json()[:limit]

        except requests.RequestException:

            logger.exception(
                "Failed to fetch Hacker News story IDs"
            )

            return []

        articles = []

        for story_id in story_ids:

            try:

                response = self.session.get(
                    f"{self.BASE_URL}/item/{story_id}.json",
                    timeout=10
                )

                response.raise_for_status()

                story = response.json()

                if not story:
                    continue

                if story.get("type") != "story":
                    continue

                if story.get("deleted") or story.get("dead"):
                    continue

                title = clean_html(
                    story.get("title", "")
                )

                article_url = story.get("url", "")

                # Ignore text-only Ask HN posts for now.
                if not title or not article_url:
                    continue

                timestamp = story.get("time")

                published_at = (
                    datetime.fromtimestamp(
                        timestamp,
                        tz=timezone.utc
                    )
                    if timestamp
                    else None
                )

                articles.append({
                    "title": title,
                    "description": clean_html(
                        story.get("text", "")
                    ),
                    "url": normalize_url(article_url),
                    "author": story.get("by", ""),
                    "published_at": published_at,
                    "external_id": str(story_id),
                })

            except (
                requests.RequestException,
                ValueError,
                TypeError,
            ):

                logger.warning(
                    "Unable to process Hacker News story %s",
                    story_id,
                    exc_info=True
                )

        return articles