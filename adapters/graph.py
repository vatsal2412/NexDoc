"""Semantic Graph Builder

This module converts one or more Artifacts into a unified Semantic Graph,
connecting cross-artifact relationships and representing everything as
nodes and edges in a standard JSON structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adapters.common.schema import Artifact


@dataclass
class GraphNode:
    id: str
    type: str
    label: str | None
    confidence: float
    source_artifact: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "confidence": self.confidence,
            "source_artifact": self.source_artifact,
            "properties": self.properties,
        }


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "confidence": self.confidence,
        }


@dataclass
class SemanticGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata,
        }

    def add_artifact(self, artifact: Artifact):
        """Adds all regions from an artifact as nodes, and their relationships as edges."""
        artifact_id = artifact.artifact
        
        # Create a document/artifact node itself
        self.nodes.append(GraphNode(
            id=f"artifact:{artifact_id}",
            type="artifact",
            label=artifact_id,
            confidence=1.0,
            source_artifact=artifact_id,
            properties={"kind": artifact.kind, "adapter": artifact.adapter}
        ))
        
        for region in artifact.regions:
            # The region node
            node_id = f"{artifact_id}::{region.id}"
            self.nodes.append(GraphNode(
                id=node_id,
                type=region.type,
                label=region.text,
                confidence=region.confidence,
                source_artifact=artifact_id,
                properties={"shape": region.shape, "language": region.language}
            ))
            
            # An edge from the artifact to the region
            self.edges.append(GraphEdge(
                source=f"artifact:{artifact_id}",
                target=node_id,
                type="contains",
                confidence=1.0
            ))
            
            for rel in region.relationships:
                target_id = rel.target
                # If target looks like a cross-artifact reference, we need to resolve it.
                # Currently schema just holds string targets.
                # Assuming targets inside the same artifact just use the region ID:
                full_target_id = f"{artifact_id}::{target_id}" if "::" not in target_id else target_id
                
                self.edges.append(GraphEdge(
                    source=node_id,
                    target=full_target_id,
                    type=rel.type,
                    confidence=region.confidence # Edge confidence inherits from source region for now
                ))

def build_graph(artifacts: list[Artifact]) -> SemanticGraph:
    graph = SemanticGraph(metadata={"version": "1.0", "artifact_count": len(artifacts)})
    for artifact in artifacts:
        graph.add_artifact(artifact)
    return graph
