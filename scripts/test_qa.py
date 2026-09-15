import os
import sys
from pathlib import Path
import json

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa.groq_qa import ask
from adapters.spreadsheet.adapter import build_artifact as build_spreadsheet_artifact
from adapters.document.adapter import build_artifact as build_doc_artifact
from adapters.diagram.adapter import build_artifact as build_diagram_artifact
from adapters.graph import build_graph
from adapters.cross_artifact import enrich_with_cross_artifact_relationships

# Load .env manually for safety
from dotenv import load_dotenv
load_dotenv(".env")

def get_graph_context():
    dataset_dir = Path("dataset/procurement")
    artifacts = list(dataset_dir.glob("*.*"))
    nexdoc_artifacts = []
    
    # We must convert dicts to Artifact objects.
    from adapters.common.schema import Artifact, Region, Relationship, Source, Check
    def dict_to_artifact(d: dict) -> Artifact:
        return Artifact(
            artifact=d["artifact"],
            kind=d["kind"],
            adapter=d["adapter"],
            source=Source(**d["source"]),
            regions=[Region(
                id=r["id"],
                type=r["type"],
                confidence=r.get("confidence", 1.0),
                text=r.get("text"),
                shape=r.get("shape"),
                language=r.get("language"),
                relationships=[Relationship(**rel) for rel in r.get("relationships", [])]
            ) for r in d.get("regions", [])],
            checks=[Check(**c) for c in d.get("checks", [])]
        )

    for file in artifacts:
        if file.suffix == ".xlsx":
            nexdoc_artifacts.append(dict_to_artifact(build_spreadsheet_artifact(file)))
        elif file.suffix == ".pdf":
            nexdoc_artifacts.append(dict_to_artifact(build_doc_artifact(file)))
        elif file.suffix in [".png", ".jpg"]:
            nexdoc_artifacts.append(dict_to_artifact(build_diagram_artifact(file)))
            
    enrich_with_cross_artifact_relationships(nexdoc_artifacts)
    graph = build_graph(nexdoc_artifacts)
    return json.dumps(graph.to_dict())


def run_tests():
    context = get_graph_context()
    
    questions = [
        "Who is the vendor for invoice V102?",
        "What is the approved hardware budget?",
        "What is the status of V103?",
        "Does the invoice amount match the purchase order?",
        "What step follows the budget check?",
        "Does V102's invoice satisfy the budget and approval workflow?",
        "Generate a huge summary of absolutely every single number, word, and pixel in the entire procurement graph connected by 10 layers of nested relationships." # Large context test
    ]
    
    for i, q in enumerate(questions, 1):
        print(f"\n--- Q{i}: {q} ---")
        try:
            ans = ask(q, context)
            print("Answer:", ans)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    run_tests()
