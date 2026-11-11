import logging
import feedparser

from urllib.parse import urlencode
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils import dateparse
from datetime import datetime, timezone as dt_timezone

from .common import clean_html, normalize_url


logger = logging.getLogger(__name__)


class GoogleNewsService:

    BASE_URL = "https://news.google.com/rss/search"

    def fetch_news(self, query, limit=15):

        params = {
            "q": query,
            "hl": "en-IN",
            "gl": "IN",
            "ceid": "IN:en",
        }

        url = f"{self.BASE_URL}?{urlencode(params)}"

        feed = feedparser.parse(url)

        if feed.bozo:
            logger.warning(
                "Google News RSS parsing warning: %s",
                feed.bozo_exception
            )

        articles = []

        for entry in feed.entries[:limit]:

            title = clean_html(
                entry.get("title", "")
            )

            article_url = normalize_url(
                entry.get("link", "")
            )

            if not title or not article_url:
                continue

            published_at = None

            if entry.get("published_parsed"):
                import calendar

                timestamp = calendar.timegm(
                    entry.published_parsed
                )

                published_at = datetime.fromtimestamp(
                    timestamp,
                    tz=dt_timezone.utc
                )

            description = clean_html(
                entry.get("summary", "")
            )

            articles.append({
                "title": title,
                "description": description,
                "url": article_url,
                "author": "",
                "published_at": published_at,
                "external_id": entry.get("id", ""),
            })

        return articles