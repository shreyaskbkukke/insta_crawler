from ..config import Settings
from .base import DataSource
from .graph import GraphAPIDataSource


def build_data_source(settings: Settings) -> DataSource:
    return GraphAPIDataSource(
        settings.ig_access_token,
        settings.ig_user_id,
        settings.graph_api_version,
        settings.graph_page_size,
    )
