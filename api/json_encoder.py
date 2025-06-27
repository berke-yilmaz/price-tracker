# api/json_encoder.py
import json
from decimal import Decimal
from datetime import date, datetime

class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle special data types that the default
    JSON encoder can't handle, like Decimal and datetime objects.
    """
    def default(self, obj):
        # Handle Decimal objects by converting them to strings
        if isinstance(obj, Decimal):
            return str(obj)
        
        # Handle date and datetime objects
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
            
        # Let the base class default method raise the TypeError
        return super().default(obj)