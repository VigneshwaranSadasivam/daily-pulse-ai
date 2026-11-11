
import time
import logging

from google import genai
from google.genai import types

from django.conf import settings
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class TagSuggestions(BaseModel):
    tags: list[str] = Field(
        description="Relevant subtopics and search keywords"
    )


class GeminiService:

    def __init__(self):
        project_id = settings.GOOGLE_CLOUD_PROJECT
        location = settings.GOOGLE_CLOUD_LOCATION

        if not project_id:
            raise ValueError(
                "Google Cloud project ID is not configured"
            )

        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )

        self.model = settings.GEMINI_MODEL

    def generate_tags(self, interest, description=""):

        prompt = f"""
You are an expert news research assistant.

Generate 8 to 12 useful news discovery tags
for the following user interest.

Interest: {interest}
Description: {description}

Requirements:
1. Generate relevant subtopics.
2. Include related technologies and concepts.
3. Include important industry keywords.
4. Avoid unrelated topics.
5. Avoid duplicate tags.
6. Keep tags concise and useful for news searching.
7. Do not generate overly broad generic words.

Return the result using the requested structured format.
"""

        max_retries = 3

        for attempt in range(max_retries):

            try:
                logger.info(
                    "Vertex AI request attempt %s for interest: %s",
                    attempt + 1,
                    interest
                )

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=TagSuggestions,
                        temperature=0.3,
                    )
                )

                if not response.text:
                    raise ValueError(
                        "Vertex AI returned an empty response"
                    )

                result = TagSuggestions.model_validate_json(
                    response.text
                )

                unique_tags = {}

                for tag in result.tags:

                    if not isinstance(tag, str):
                        continue

                    tag = tag.strip()

                    if tag:
                        unique_tags.setdefault(
                            tag.casefold(),
                            tag
                        )

                tags = list(unique_tags.values())

                logger.info(
                    "Generated %s unique tags for interest: %s",
                    len(tags),
                    interest
                )

                return tags

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
                    logger.exception(
                        "Vertex AI tag generation failed"
                    )
                    raise

                delay = 2 ** (attempt + 1)

                logger.warning(
                    "Vertex AI temporarily unavailable. "
                    "Retrying in %s seconds. Error: %s",
                    delay,
                    error_message
                )

                time.sleep(delay)

        raise RuntimeError(
            "Vertex AI tag generation failed"
        )
