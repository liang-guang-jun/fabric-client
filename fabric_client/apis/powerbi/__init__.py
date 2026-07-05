"""Power BI REST API clients."""

from __future__ import annotations

from fabric_client.apis.powerbi.dataflows import DataflowsAPI
from fabric_client.apis.powerbi.datasets import DatasetsAPI
from fabric_client.apis.powerbi.reports import ReportsAPI

__all__ = ["DataflowsAPI", "DatasetsAPI", "ReportsAPI"]
