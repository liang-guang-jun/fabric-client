"""Domain model classes for Fabric / Power BI resources."""

from __future__ import annotations

from fabric_client.models.dataflow import Dataflow, DataflowModel
from fabric_client.models.dataset import Dataset, DatasetModel
from fabric_client.models.report import Report, ReportModel
from fabric_client.models.semantic_model import (
    SemanticModel,
    SemanticModelModel,
)
from fabric_client.models.workspace import Workspace, WorkspaceModel

__all__ = [
    "Dataflow",
    "DataflowModel",
    "Dataset",
    "DatasetModel",
    "Report",
    "ReportModel",
    "SemanticModel",
    "SemanticModelModel",
    "Workspace",
    "WorkspaceModel",
]
