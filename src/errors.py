"""The one error type the service layer raises when a business rule is broken.

Routes turn it into a page message or a JSON body {"error": ..., "rule": ...} with its
HTTP status (docs/design.md section 3). The message is the exact sentence from the
acceptance criterion, so tests and screens can match it word for word.
"""


class BusinessRuleError(Exception):
    """A request broke a business rule.

    Accepts either calling convention:
      - BusinessRuleError(status, message, rule=None, field=None)
      - BusinessRuleError(rule, message, status=422, field=None)
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
        return {"error": self.message, "rule": self.rule, "field": self.field}