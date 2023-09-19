from pydantic_settings import BaseSettings


class Config(BaseSettings):
    api_key: str
    is_demo: bool = False
    api_version: int = 0

    # computed in init
    base_url: str = "https://{}.trading212.com/api/v{}/equity".format(
            "demo" if is_demo else "live",
            api_version,
        )


    class Config:
        env_file = ".env"


config = Config()
