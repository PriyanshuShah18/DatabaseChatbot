from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal, Any


class AggregationModel(BaseModel):
    group_by: Optional[str] = Field(None, description="The field to group by (e.g., 'client_name', 'status').")
    operation: Literal["sum", "count", "avg", "max", "min"] = Field("sum", description="The aggregation operation to perform.")
    field: Optional[str] = Field(None, description="The numeric field to aggregate (e.g., 'total', 'price').")

class SortModel(BaseModel):
    field: str = Field(description="The field to sort by.")
    order: Literal["asc", "desc"] = Field("desc", description="Sort order.")

class QueryPlan(BaseModel):
    """
    A structured plan to query the CodnestX MongoDB database.
    """
    collection: Optional[str] = Field(None, description="The name of the MongoDB collection to query.")
    filters: dict = Field(default_factory=dict, description="Key-value pairs for filtering documents.")
    aggregation: Optional[AggregationModel] = Field(None, description="Optional aggregation pipeline details.")
    sort: Optional[SortModel] = Field(None, description="Optional sorting details.")
    limit: Optional[int] = Field(10, description="The maximum number of records to return.")
    fields: List[str] = Field(default_factory=list, description="Specific fields to include in the result.")

    @field_validator('filters', mode='before')
    @classmethod
    def ensure_dict(cls, v: Any) -> dict:
        if isinstance(v, list) or v is None:
            return {}
        return v

    @field_validator('limit', mode='before')
    @classmethod
    def ensure_int(cls, v: Any) -> int:
        if v is None or v == "":
            return 10
        try:
            return int(v)
        except (ValueError, TypeError):
            return 10

    @field_validator('fields', mode='before')
    @classmethod
    def clean_fields(cls, v: Any) -> List[str]:
        if v is None: return []
        if isinstance(v, list):
            # Remove wildcard patterns often hallucinated by AI
            return [f for f in v if f != "*"]
        return []