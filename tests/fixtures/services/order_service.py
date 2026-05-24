from appctx.decorators import component
from tests.fixtures.config import AppConfig, DbConfig


@component
class OrderService:
    def __init__(self, db_config: DbConfig):
        self.db_config = db_config


@component(name="premium_order_service")
class PremiumOrderService:
    def __init__(self, db_config: DbConfig, app_config: AppConfig):
        self.db_config = db_config
        self.app_config = app_config
