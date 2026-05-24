from appctx.decorators import component
from tests.fixtures.config import DbConfig


@component
class UserService:
    def __init__(self, db_config: DbConfig):
        self.db_config = db_config
