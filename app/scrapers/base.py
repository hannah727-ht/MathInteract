

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.robotparser import RobotFileParser

import truststore

USER_AGENT = "MathInteractBot/1.0 (non-commercial student math site)"
DELAY_SECONDS = 1.5
TIMEOUT_SECONDS = 30




SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


@dataclass(frozen=True)
class Item:


    section: str
    contest: str
    year: int | None
    title: str
    kind: str
    url: str
    download: bool


class BlockedByRobots(Exception):
    pass


class Fetcher:






    def __init__(self) -> None:
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser] = {}

    def _open(self, url: str):
        host = urlsplit(url).netloc
        wait = self._last_request.get(host, 0) + DELAY_SECONDS - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=SSL_CONTEXT)
        finally:
            self._last_request[host] = time.monotonic()

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            parser = RobotFileParser()
            try:
                with self._open(f"{host}/robots.txt") as res:
                    parser.parse(res.read().decode("utf-8", "replace").splitlines())
            except urllib.error.HTTPError as e:
                if e.code >= 500:
                    raise
                parser.parse([])
            self._robots[host] = parser
        return self._robots[host].can_fetch(USER_AGENT, url)

    def get(self, url: str, params: dict | None = None):

        if params:
            url = f"{url}?{urlencode(params)}"
        if not self._allowed(url):
            raise BlockedByRobots(url)
        return self._open(url)

    def text(self, url: str, params: dict | None = None) -> str:
        with self.get(url, params) as res:
            return res.read().decode(res.headers.get_content_charset() or "utf-8", "replace")

    def json(self, url: str, params: dict | None = None) -> dict:
        return json.loads(self.text(url, params))

    def download(self, url: str, dest: Path, max_bytes: int) -> int:

        size = 0
        with self.get(url) as res:
            try:
                with dest.open("wb") as out:
                    chunk = res.read(64 * 1024)
                    while chunk:
                        if size == 0 and not chunk.startswith(b"%PDF-"):
                            raise ValueError("not a PDF")
                        size += len(chunk)
                        if size > max_bytes:
                            raise ValueError("file too large")
                        out.write(chunk)
                        chunk = res.read(64 * 1024)
                if size == 0:
                    raise ValueError("empty file")
            except BaseException:
                dest.unlink(missing_ok=True)
                raise
        return size
