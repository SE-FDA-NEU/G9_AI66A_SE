"""The one exception every business rule raises.

Services raise it; routes turn it into a page with a clear message, or into the JSON
error {"error": ..., "rule": ...} listed in docs/design.md section 3.
"""


class BusinessRuleError(Exception):
    """A request broke a business rule.

    status  - the HTTP code from the API table in docs/design.md section 3
    message - the exact sentence the user sees (docs/ui.md section 3)
    rule    - the business rule, e.g. "BR11" (docs/requirements.md section 5)
    field   - the form field the message belongs next to, if any
    """

    def __init__(self, status, message, rule=None, field=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.rule = rule
        self.field = field

    def to_json(self):
        body = {"error": self.message}
        if self.rule:
            body["rule"] = self.rule
        return body
