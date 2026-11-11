
import logging
import time

from django.conf import settings
from django.utils import timezone

from google import genai
from google.genai import types

from interests.models import Article
from interests.services.ai.schemas import ArticleIntelligence


logger = logging.getLogger(__name__)


class ArticleIntelligenceService:

    def __init__(self):

        self.client = genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
        )

        self.model = settings.GEMINI_MODEL

    def analyze_article(self, article):

        if article.ai_status == Article.AIStatus.COMPLETED:
            logger.info(
                "Article already analyzed: %s",
                article.id
            )
            return None

        prompt = f"""
You are an expert news analyst working for DailyPulse AI.

Analyze the following news article and return structured information.

ARTICLE TITLE:
{article.title}

ARTICLE DESCRIPTION:
{article.description}

ARTICLE AUTHOR:
{article.author}

PUBLISHED DATE:
{article.published_at}

TASKS:

1. SUMMARY:
Write a factual summary in 3 to 5 sentences.
Do not invent facts that are not present in the article.

2. CATEGORY:
Select one primary category:
Artificial Intelligence, Technology, Business,
Science, Cybersecurity, Finance, Politics,
Health, World News, or Other.

3. KEYWORDS:
Extract 5 to 10 meaningful keywords.
Include relevant technologies, companies,
people, products, and concepts.

4. IMPORTANCE SCORE:
Give an importance score between 1 and 100.
Consider the potential impact, novelty,
industry significance, and relevance.

If information is insufficient, clearly reflect
that limitation in the summary.

Return only the requested structured response.
"""

        max_retries = 3

        for attempt in range(max_retries):

            try:

                logger.info(
                    "Analyzing article ID %s, attempt %s",
                    article.id,
                    attempt + 1
                )

                article.ai_status = Article.AIStatus.PROCESSING
                article.ai_error = ""
                article.save(
                    update_fields=["ai_status", "ai_error"]
                )

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ArticleIntelligence,
                        temperature=0.2,
                    )
                )

                if not response.text:
                    raise ValueError(
                        "Vertex AI returned an empty response"
                    )

                result = ArticleIntelligence.model_validate_json(
                    response.text
                )

                article.ai_summary = result.summary.strip()
                article.ai_category = result.category.strip()
                article.ai_keywords = list(
                    dict.fromkeys(
                        keyword.strip()
                        for keyword in result.keywords
                        if keyword and keyword.strip()
                    )
                )[:10]

                article.ai_importance_score = (
                    result.importance_score
                )

                article.ai_model = self.model
                article.ai_status = Article.AIStatus.COMPLETED
                article.ai_analyzed_at = timezone.now()
                article.ai_error = ""

                article.save(
                    update_fields=[
                        "ai_summary",
                        "ai_category",
                        "ai_keywords",
                        "ai_importance_score",
                        "ai_model",
                        "ai_status",
                        "ai_analyzed_at",
                        "ai_error",
                    ]
                )

                logger.info(
                    "Article analysis completed: %s",
                    article.id
                )

                return result

            except Exception as exc:

                error_message = str(exc)

                retryable = any(
                    code in error_message
                    for code in [
                        "429",
                        "500",
                        "502",
                        "503",
                        "504",
                    ]
                )

                if (
                    not retryable
                    or attempt == max_retries - 1
                ):

                    article.ai_status = Article.AIStatus.FAILED
                    article.ai_error = error_message[:2000]

                    article.save(
                        update_fields=[
                            "ai_status",
                            "ai_error",
                        ]
                    )

                    logger.exception(
                        "Article analysis failed: %s",
                        article.id
                    )

                    raise

                delay = 2 ** (attempt + 1)

                logger.warning(
                    "Vertex AI temporarily unavailable. "
                    "Retrying in %s seconds.",
                    delay
                )

                time.sleep(delay)

        raise RuntimeError(
            "Article intelligence processing failed"
        )
