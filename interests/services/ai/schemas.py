
from pydantic import BaseModel, Field


class ArticleIntelligence(BaseModel):

    summary: str = Field(
        description=(
            "A clear, factual summary of the article "
            "in approximately 3 to 5 sentences."
        )
    )

    category: str = Field(
        description=(
            "One primary category such as AI, Technology, "
            "Business, Science, Cybersecurity, Finance, "
            "Politics, Health, or World News."
        )
    )

    keywords: list[str] = Field(
        description=(
            "5 to 10 important topics, technologies, "
            "companies, people, or concepts mentioned "
            "in the article."
        )
    )

    importance_score: int = Field(
        ge=1,
        le=100,
        description=(
            "Importance of this news article on a scale "
            "from 1 to 100. Consider impact, relevance, "
            "novelty, and significance."
        )
    )
