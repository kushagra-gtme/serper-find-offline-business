"""Data models for Serper Places search."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class Query:
    """A single search query for Serper Places API."""
    q: str
    location: str
    page: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Query":
        return cls(**data)


@dataclass
class Place:
    """A place result from Serper Places API."""
    q: str
    location: str
    page: int
    position: int
    title: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    ratingCount: Optional[int] = None
    category: Optional[str] = None
    phoneNumber: Optional[str] = None
    website: Optional[str] = None
    website_normalized: Optional[str] = None
    cid: Optional[str] = None

    def to_csv_row(self) -> List[str]:
        return [
            self.q,
            self.location,
            str(self.page),
            str(self.position),
            self.title or "NA",
            self.address or "NA",
            str(self.latitude) if self.latitude is not None else "NA",
            str(self.longitude) if self.longitude is not None else "NA",
            str(self.rating) if self.rating is not None else "NA",
            str(self.ratingCount) if self.ratingCount is not None else "NA",
            self.category or "NA",
            self.phoneNumber or "NA",
            self.website or "NA",
            self.website_normalized or "NA",
            self.cid or "NA",
        ]

    @staticmethod
    def csv_headers() -> List[str]:
        return [
            "q", "location", "page", "position", "title", "address",
            "latitude", "longitude", "rating", "ratingCount",
            "category", "phoneNumber", "website", "website_normalized", "cid",
        ]


@dataclass
class RunConfig:
    """Configuration for a search run."""
    run_id: str
    created_at: datetime
    states: List[str]
    search_terms: List[str]
    pages_per_query: int
    total_queries: int
    cities: Optional[List[str]] = None
    webhook_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at.isoformat(),
            "states": self.states,
            "search_terms": self.search_terms,
            "pages_per_query": self.pages_per_query,
            "total_queries": self.total_queries,
            "cities": self.cities,
            "webhook_url": self.webhook_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunConfig":
        data = dict(data)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        valid_fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid_fields})


@dataclass
class RunProgress:
    """Execution progress tracking."""
    total_queries: int
    total_batches: int
    completed_batches: int = 0
    failed_queries: int = 0
    last_updated: Optional[datetime] = None
    status: str = "created"
    current_batch: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "total_batches": self.total_batches,
            "completed_batches": self.completed_batches,
            "failed_queries": self.failed_queries,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "status": self.status,
            "current_batch": self.current_batch,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunProgress":
        data = dict(data)
        if data.get("last_updated"):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        valid_fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid_fields})


@dataclass
class PlaceFilters:
    """Filtering and deduplication criteria."""
    min_rating: Optional[float] = None
    min_review_count: Optional[int] = None
    require_phone: Optional[bool] = None
    require_website: Optional[bool] = None
    require_address: Optional[bool] = None
    exclude_keywords: Optional[List[str]] = None
    dedupe_by: str = "both"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaceFilters":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
