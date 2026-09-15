"""Cross-Artifact Relationship Resolver

This module takes a list of Artifacts and looks for defensible links between them,
such as matching Vendor IDs, matching amounts (e.g. invoice total to approved budget),
or matching identifiers across spreadsheets, diagrams, and documents.
"""

from __future__ import annotations

from typing import Iterable

from adapters.common.schema import Artifact, Region, Relationship


def find_vendor_id(region: Region) -> str | None:
    # Extremely basic heuristic for extracting a vendor ID like "V102"
    if not region.text:
        return None
    import re
    # Match V followed by 2-4 digits as a simple vendor ID pattern
    m = re.search(r'\bV\d{2,4}\b', region.text)
    if m:
        return m.group(0)
    return None

def find_amount(region: Region) -> float | None:
    # Heuristic to find an amount
    if not region.text:
        return None
    import re
    # Match something that looks like an amount (e.g. 18400 or 18,400.00)
    # Exclude basic dates
    m = re.search(r'\b(?:total|amount|sum)?\s*:?\s*[\$€£]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b', region.text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(',', ''))
        except ValueError:
            pass
    return None

def _resolve_relationships_between(artifacts: list[Artifact]):
    # Build indexes
    vendor_nodes = []
    amount_nodes = []
    
    for artifact in artifacts:
        for region in artifact.regions:
            vid = find_vendor_id(region)
            if vid:
                vendor_nodes.append((vid, artifact.artifact, region))
            
            amt = find_amount(region)
            if amt is not None:
                amount_nodes.append((amt, artifact.artifact, region))
                
    # Create relationships for matching Vendor IDs
    for i in range(len(vendor_nodes)):
        vid1, art1, reg1 = vendor_nodes[i]
        for j in range(i+1, len(vendor_nodes)):
            vid2, art2, reg2 = vendor_nodes[j]
            if vid1 == vid2 and art1 != art2:
                # Add relationship to reg1 pointing to reg2
                reg1.relationships.append(Relationship("cross-artifact-vendor-match", f"{art2}::{reg2.id}"))
                reg2.relationships.append(Relationship("cross-artifact-vendor-match", f"{art1}::{reg1.id}"))

    # Create relationships for matching amounts
    # (e.g., invoice total matches approved budget or payment amount)
    for i in range(len(amount_nodes)):
        amt1, art1, reg1 = amount_nodes[i]
        for j in range(i+1, len(amount_nodes)):
            amt2, art2, reg2 = amount_nodes[j]
            if amt1 == amt2 and art1 != art2:
                # Basic check to avoid linking low-confidence or tiny amounts randomly
                if amt1 > 100:
                    reg1.relationships.append(Relationship("cross-artifact-amount-match", f"{art2}::{reg2.id}"))
                    reg2.relationships.append(Relationship("cross-artifact-amount-match", f"{art1}::{reg1.id}"))

def enrich_with_cross_artifact_relationships(artifacts: list[Artifact]):
    """Modifies the passed Artifacts in-place by adding cross-artifact relationships."""
    _resolve_relationships_between(artifacts)
