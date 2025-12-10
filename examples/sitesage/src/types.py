from pydantic import BaseModel
from typing import List, Optional


class SocialLinks(BaseModel):
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    email: Optional[str] = None


class SEOInfo(BaseModel):
    canonical_url: Optional[str] = None
    robots: Optional[str] = None
    open_graph: bool = False
    twitter_cards: bool = False
    structured_data: bool = False


class WebAnalysis(BaseModel):
    site_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    technology: Optional[str] = None
    theme: Optional[str] = None
    key_features: List[str] = []
    social_links: Optional[SocialLinks] = None
    author: Optional[str] = None
    analytics: List[str] = []
    seo: Optional[SEOInfo] = None


class WebSiteAnalysisResponse(BaseModel):
    html: Optional[str] = None
    screenshot_path: Optional[str] = None
    analysis: Optional[WebAnalysis] = None
