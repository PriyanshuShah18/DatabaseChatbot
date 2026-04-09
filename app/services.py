"""
Unified Query Execution Engine
──────────────────────────────
Validates query plans produced by the LLM, maps them to the correct
MongoDB collection, and executes safe read-only queries.

NOTE: The actual MongoDB query construction / aggregation pipeline
      is deliberately left as a placeholder per user's request.
      Only the validation & security layer is implemented here.
"""

from .database import ALLOWED_COLLECTIONS, get_allowed_fields


# ── Security Validation ───────────────────────────────────────────

class QueryValidationError(Exception):
    """Raised when a query plan fails security checks."""
    pass

def _validate_plan(plan: dict) -> None:
    """Enforce security rules on the query plan before execution."""

    collection_name = plan.get("collection", "")

    # 1. Collection must be in the allowlist
    if collection_name not in ALLOWED_COLLECTIONS:
        raise QueryValidationError(
            f"Collection '{collection_name}' is not allowed. "
            f"Allowed: {list(ALLOWED_COLLECTIONS.keys())}"
        )

    allowed_fields = get_allowed_fields()
    allowed = allowed_fields.get(collection_name, [])

    # 2. Filter fields must be allowed
    for field in plan.get("filters", {}):
        if field not in allowed:
            raise QueryValidationError(
                f"Field '{field}' is not allowed on collection '{collection_name}'. "
                f"Allowed: {allowed}"
            )

    # 3. Aggregation field must be allowed
    agg = plan.get("aggregation")
    if agg and isinstance(agg, dict):
        for key in ("group_by", "field"):
            val = agg.get(key)
            # Skip if val is None, null, or the string "None"
            if val and str(val).lower() != "none" and val not in allowed:
                raise QueryValidationError(
                    f"Aggregation field '{val}' is not allowed on '{collection_name}'."
                )

    # 4. Sort field must be allowed
    sort = plan.get("sort")
    if sort and isinstance(sort, dict):
        sf = sort.get("field")
        # Skip if sf is None, null, or the string "None"
        if sf and str(sf).lower() != "none" and sf not in allowed:
            raise QueryValidationError(
                f"Sort field '{sf}' is not allowed on '{collection_name}'."
            )

    # 5. Projected fields must be allowed
    for field in plan.get("fields", []):
        if field not in allowed:
            raise QueryValidationError(
                f"Projection field '{field}' is not allowed on '{collection_name}'."
            )


# ── Query Execution (Placeholder) ─────────────────────────────────

def execute_query_plan(plan: dict) -> list:
    """
    Validate the plan, then execute a safe read-only query.

    Returns a list of result dicts (with _id removed).
    """

    # Step 1 — Validate
    _validate_plan(plan)

    collection_name = plan["collection"]
    collection = ALLOWED_COLLECTIONS[collection_name]

    filters     = plan.get("filters", {})
    aggregation = plan.get("aggregation")
    sort_spec   = plan.get("sort")
    limit       = min(plan.get("limit", 10), 100)  # hard cap at 100
    fields      = plan.get("fields", [])

    # ── Build MongoDB filter ──────────────────────────────────────
    mongo_filter = {}
    for key, value in filters.items():
        if isinstance(value, str):
            # Case-insensitive regex for string filters
            mongo_filter[key] = {"$regex": value, "$options": "i"}
        else:
            mongo_filter[key] = value

    # ── Aggregation path ──────────────────────────────────────────
    if aggregation:
        group_by  = aggregation.get("group_by")
        operation = aggregation.get("operation", "sum")
        agg_field = aggregation.get("field", "total")

        op_map = {
            "sum":   {"$sum":   f"${agg_field}"},
            "count": {"$sum":   1},
            "avg":   {"$avg":   f"${agg_field}"},
            "max":   {"$max":   f"${agg_field}"},
            "min":   {"$min":   f"${agg_field}"},
        }

        pipeline = [{"$match": mongo_filter}]

        group_stage = {
            "$group": {
                "_id": f"${group_by}" if group_by else None,
                "result": op_map.get(operation, {"$sum": f"${agg_field}"}),
            }
        }
        pipeline.append(group_stage)

        if sort_spec:
            direction = 1 if sort_spec.get("order", "asc") == "asc" else -1
            pipeline.append({"$sort": {"result": direction}})

        pipeline.append({"$limit": limit})

        results = list(collection.aggregate(pipeline))
        # Clean _id
        for r in results:
            if "_id" in r and r["_id"] is not None:
                r["group"] = r.pop("_id")
            else:
                r.pop("_id", None)
        return results

    # ── Normal find path ──────────────────────────────────────────
    projection = {f: 1 for f in fields} if fields else None
    if projection:
        projection["_id"] = 0
    cursor = collection.find(mongo_filter, projection)

    if sort_spec:
        sort_field = sort_spec.get("field", "_id")
        direction  = 1 if sort_spec.get("order", "asc") == "asc" else -1
        cursor = cursor.sort(sort_field, direction)

    cursor = cursor.limit(limit)

    results = []
    for doc in cursor:
        doc.pop("_id", None)
        results.append(doc)

    return results