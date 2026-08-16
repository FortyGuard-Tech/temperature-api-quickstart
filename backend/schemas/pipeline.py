from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AgentStepResult(BaseModel):
    agent_name: str
    status: str
    summary: str
    details: Dict[str, Any]

class PipelineResponse(BaseModel):
    status: str = "success"
    total_execution_time_ms: float
    steps: List[AgentStepResult]
    summary_report: Dict[str, Any]
