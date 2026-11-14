"""Polite, reproducible downloading into the immutable ``data/raw`` tree.

Every file written under ``data/raw`` is recorded in ``data/raw/MANIFEST.json`` with its source URL,
sha256, byte size, license and fetch timestamp. Existing files are never overwritten: raw data is
immutable, and re-running the pipeline reuses the snapshot so results stay reproducible.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

USER_AGENT = "IGNIS-pipeline/0.1 (open-source research pipeline; NASA Space Apps 2026)"


@dataclass(frozen=True)
class ManifestEntry:
    path: str  # relative to data/raw, POSIX separators
    url: str
    sha256: str
    bytes: int
    license: str
    fetched_at: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


class Manifest:
    def __init__(self, raw_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.path = raw_dir / "MANIFEST.json"
        self.entries: dict[str, ManifestEntry] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for item in data["files"]:
                entry = ManifestEntry(**item)
                self.entries[entry.path] = entry

    def record(self, rel_path: str, url: str, license_id: str) -> ManifestEntry:
        file_path = self.raw_dir / rel_path
        entry = ManifestEntry(
            path=rel_path,
            url=url,
            sha256=sha256_file(file_path),
            bytes=file_path.stat().st_size,
            license=license_id,
            fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        self.entries[rel_path] = entry
        return entry

    def verify(self) -> list[str]:
        """Return the list of manifest paths whose bytes no longer match their sha256."""
        bad: list[str] = []
        for rel, entry in self.entries.items():
            fp = self.raw_dir / rel
            if not fp.exists() or sha256_file(fp) != entry.sha256:
                bad.append(rel)
        return bad

    def save(self) -> None:
        payload = {
            "description": "Immutable raw inputs of the IGNIS pipeline (sha256 per file).",
            "files": [asdict(e) for e in sorted(self.entries.values(), key=lambda e: e.path)],
        }
        self.path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


class Fetcher:
    """HTTP client that writes each response once into data/raw and records it in the manifest."""

    def __init__(self, raw_dir: Path, *, delay_s: float = 0.4, timeout_s: float = 120.0) -> None:
        self.raw_dir = raw_dir
        self.manifest = Manifest(raw_dir)
        self.delay_s = delay_s
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_s,
            follow_redirects=True,
        )

    def get_json(self, url: str) -> object:
        response = self._get(url)
        return response.json()

    def download(self, url: str, rel_path: str, license_id: str, *, refresh: bool = False) -> Path:
        """Download ``url`` to ``data/raw/rel_path`` unless it already exists (immutability)."""
        target = self.raw_dir / rel_path
        if target.exists() and not refresh:
            if rel_path not in self.manifest.entries:
                self.manifest.record(rel_path, url, license_id)
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        response = self._get(url)
        if not response.content:
            raise RuntimeError(f"Empty response for {url}")
        target.write_bytes(response.content)
        self.manifest.record(rel_path, url, license_id)
        return target

    def _get(self, url: str) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                response = self.client.get(url)
                if response.status_code in (429, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"retryable {response.status_code}", request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                time.sleep(self.delay_s)
                return response
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
                    raise
                time.sleep(2.0 * (attempt + 1))
        raise RuntimeError(f"GET failed after retries: {url}") from last_exc

    def close(self) -> None:
        self.manifest.save()
        self.client.close()
