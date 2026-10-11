"""The one error type the service layer raises when a business rule is broken.

Routes turn it into a page message or a JSON body {"error": ..., "rule": ...} with its
HTTP status (docs/design.md section 3). The message is the exact sentence from the
acceptance criterion, so tests and screens can match it word for word.
"""


class BusinessRuleError(Exception):
    def __init__(self, rule, message, status=422):
        super().__init__(message)
        self.rule = rule          # e.g. "BR11"
        self.message = message
        self.status = status

    def as_json(self):
        return {"error": self.message, "rule": self.rule}
