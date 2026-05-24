from appctx.decorators import bean


class DbConfig:
    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port


class AppConfig:
    def __init__(self, name: str = "my_app"):
        self.name = name


@bean
def db_config():
    return DbConfig()


@bean(name="app_config")
def application_config():
    return AppConfig()
