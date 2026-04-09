from pymongo import MongoClient
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

@lru_cache(maxsize=1)
def extract_schema():
    """
    Dynamically extract collection names, field types, and sample entities.
    """
    schema = {}
    
    # Key fields to extract sample values from for entity awareness
    entity_fields = ["client_name", "vendor_name", "service_name", "account_name", "invoice_number"]

    for collection_name in db.list_collection_names():
        # Get structure
        sample_docs = list(db[collection_name].find().limit(5))
        fields = {}
        for doc in sample_docs:
            for key, value in doc.items():
                if key not in fields and key != "_id":
                    fields[key] = type(value).__name__

        # Extract sample entity values
        samples = {}
        for field in entity_fields:
            if field in fields:
                unique_values = db[collection_name].distinct(field)
                samples[field] = unique_values[:10]  # Limit to 10 for context window

        schema[collection_name] = {
            "fields": fields,
            "sample_entities": samples
        }

    return schema