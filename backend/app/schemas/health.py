from typing import Dict, Optional
from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    status: str = Field(..., description="Component status: healthy, unhealthy, degraded, or disabled")
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall platform status")
    environment: str = Field(..., description="Current deployment environment")
    version: str = Field("0.1.0", description="Backend application version")
    components: Dict[str, ComponentHealth] = Field(..., description="Detailed status breakdown by component")
