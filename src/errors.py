"""The one exception every business rule raises.

Services raise it; routes turn it into a page with a clear message, or into the JSON
error {"error": ..., "rule": ...} listed in docs/design.md section 3.
"""


class BusinessRuleError(Exception):
    """A request broke a business rule.

    Accepts either calling convention:
      - BusinessRuleError(status, message, rule=None, field=None)   (US02 / #64)
      - BusinessRuleError(rule, message, status=422, field=None)   (US05 / #68)

    status  - the HTTP code from the API table in docs/design.md section 3
    message - the exact sentence the user sees (docs/ui.md section 3)
    rule    - the business rule, e.g. "BR11" (docs/requirements.md section 5)
    field   - the form field the message belongs next to, if any
    """

    def __init__(self, arg1, message, arg3=None, field=None):
        super().__init__(message)
        self.message = message
        self.field = field
        if isinstance(arg1, int):
            self.status = arg1
            self.rule = arg3
        else:
            self.rule = arg1
            self.status = arg3 if arg3 is not None else 422

    def to_json(self):
        body = {"error": self.message}
        if self.rule:
            body["rule"] = self.rule
        return body

    def as_json(self):
        return self.to_json()
