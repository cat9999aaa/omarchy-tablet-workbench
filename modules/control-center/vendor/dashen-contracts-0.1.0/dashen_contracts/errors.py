"""Public errors contain stable codes, never source payloads."""


class ContractError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
