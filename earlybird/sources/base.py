from __future__ import annotations

import abc
import logging

import httpx

from earlybird.config import HTTP_TIMEOUT, USER_AGENT
from earlybird.models import Item

log = logging.getLogger(__name__)


class Source(abc.ABC):
    """Base class for every content source."""

    name: str  # unique key, e.g. "arxiv"

    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    # ── public API ───────────────────────────────────────────────────────
    def fetch(self) -> list[Item]:
        log.info("fetching %s", self.name)
        try:
            items = self._fetch()
            log.info("fetched %d items from %s", len(items), self.name)
            return items
        except Exception:
            log.exception("error fetching %s", self.name)
            return []

    # ── subclass contract ────────────────────────────────────────────────
    @abc.abstractmethod
    def _fetch(self) -> list[Item]:
        ...

    # ── helpers ──────────────────────────────────────────────────────────
    def _get(self, url: str, **kwargs) -> httpx.Response:
        resp = self.client.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        self.client.close()
