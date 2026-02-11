from pydantic_settings import BaseSettings


class IngestionSettings(BaseSettings):
    udp_ip: str = "127.0.0.1"
    udp_port: int = 5005

    satellite_id: int = 1
    metric_voltage: int = 1
    metric_temperature: int = 2

    header_format: str = "!HHI"
    header_size: int = 6

    telemetry_id: int = 100
    command_id: int = 200

    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_user: str = 'postgres'
    postgres_password: str = 'space'
    postgres_db: str = 'space'
    postgres_uri: str = f"postgres://{postgres_user}:{postgres_password}@{postgres_host}/{postgres_db}"

    redis_host: str = 'localhost'
    redis_port: int = 6379
    redis_db: int = 0


def get_ingestion_settings() -> IngestionSettings:
    return IngestionSettings()

