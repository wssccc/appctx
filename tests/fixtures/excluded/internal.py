from appctx.decorators import component


@component
class InternalService:
    def __init__(self):
        self.name = "internal"
