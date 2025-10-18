"""Planetary charter codifying global rights and duties."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, MutableMapping, Optional

from genesis.metanet.models import LawArticle


@dataclass(slots=True)
class CharterArticle:
    identifier: str
    title: str
    text: str
    version: int = 1
    active: bool = True


class GlobalCharter:
    """Maintains the canonical set of planetary law articles."""

    def __init__(self) -> None:
        self._articles: MutableMapping[str, CharterArticle] = {}

    def add_article(self, article: CharterArticle) -> None:
        self._articles[article.identifier] = article

    def amend(self, identifier: str, *, text: Optional[str] = None, active: Optional[bool] = None) -> CharterArticle:
        article = self._articles[identifier]
        if text is not None:
            article.text = text
            article.version += 1
        if active is not None:
            article.active = active
        self._articles[identifier] = article
        return article

    def list_articles(self, include_inactive: bool = False) -> Iterable[CharterArticle]:
        if include_inactive:
            return tuple(self._articles.values())
        return tuple(article for article in self._articles.values() if article.active)

    def to_model(self, article: CharterArticle) -> LawArticle:
        return LawArticle(
            id=None,
            title=article.title,
            text=article.text,
            version=article.version,
            active=article.active,
        )


__all__ = ["GlobalCharter", "CharterArticle"]
