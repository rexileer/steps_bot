from django.db.models import JSONField as DjangoJSONField
import json


class SafeJSONField(DjangoJSONField):
    def from_db_value(self, value, expression, connection):
        if isinstance(value, dict):
            return value
        if value is None:
            return None
        return json.loads(value)