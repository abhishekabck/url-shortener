from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime

class URLCreate(BaseModel):
    original_url: HttpUrl

class URLResponse(BaseModel):
    short_code: str
    original_url: HttpUrl
    short_url: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class URLStats(BaseModel):
    short_code: str
    original_url: HttpUrl
    click_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

