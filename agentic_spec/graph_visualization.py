"""Graph visualization for specification relationships."""

from pathlib import Path
from typing import Any

from .core import SpecGenerator

try:
    import matplotlib.pyplot as plt
    import networkx as nx

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False


def visualize_spec_graph(specs_dir: Path, output_file: str = "spec_graph.png"):
    """Create a visual graph of specification relationships."""

    if not VISUALIZATION_AVAILABLE:
        print(
            "Visualization libraries not available. Install matplotlib and networkx for graph visualization."
        )
        return

    # Initialize generator to access graph methods
    generator = SpecGenerator(Path("templates"), specs_dir)
    spec_graph = generator.get_spec_graph()

    if not spec_graph:
        print("No specifications found to visualize")
        return

    # Create NetworkX graph
    G = nx.DiGraph()

    # Add nodes
    for spec_id, spec_data in spec_graph.items():
        spec = spec_data["spec"]
        G.add_node(
            spec_id,
            label=f"{spec_id[:8]}\n{spec.context.project}",
            status=spec.metadata.status,
        )

    # Add edges (parent -> child relationships)
    for spec_id, spec_data in spec_graph.items():
        parent_id = spec_data["parent"]
        if parent_id and parent_id in spec_graph:
            G.add_edge(parent_id, spec_id)

    # Set up the plot
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=3, iterations=50)

    # Color nodes by status
    status_colors = {
        "draft": "lightblue",
        "reviewed": "yellow",
        "approved": "lightgreen",
        "implemented": "darkgreen",
    }

    node_colors = [
        status_colors.get(G.nodes[node].get("status", "draft"), "lightgray")
        for node in G.nodes()
    ]

    # Draw the graph
    nx.draw(
        G,
        pos,
        node_color=node_colors,
        node_size=2000,
        with_labels=True,
        labels={node: G.nodes[node]["label"] for node in G.nodes()},
        font_size=8,
        font_weight="bold",
        arrows=True,
        arrowsize=20,
        edge_color="gray",
        alpha=0.7,
    )

    plt.title("Specification Relationship Graph", fontsize=16, fontweight="bold")

    # Add legend
    legend_elements = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=color,
            markersize=10,
            label=status.title(),
        )
        for status, color in status_colors.items()
    ]
    plt.legend(handles=legend_elements, loc="upper right")

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Graph visualization saved to {output_file}")
    plt.show()


def print_spec_graph(specs_dir: Path):
    """Print a text-based representation of the specification graph."""

    generator = SpecGenerator(Path("templates"), specs_dir)
    spec_graph = generator.get_spec_graph()

    if not spec_graph:
        print("No specifications found")
        return

    print("📊 Specification Graph:")
    print("=" * 50)

    # Find root specs (no parent)
    root_specs = [spec_id for spec_id, data in spec_graph.items() if not data["parent"]]

    def print_spec_tree(spec_id: str, indent: int = 0):
        """Recursively print specification tree."""
        if spec_id not in spec_graph:
            return

        spec_data = spec_graph[spec_id]
        spec = spec_data["spec"]

        prefix = "  " * indent + ("├─ " if indent > 0 else "")
        status_emoji = {
            "draft": "📝",
            "reviewed": "👀",
            "approved": "✅",
            "implemented": "🚀",
        }.get(spec.metadata.status, "❓")

        print(f"{prefix}{status_emoji} {spec_id[:8]} - {spec.context.project}")
        print(f"{'  ' * (indent + 1)}📁 {spec_data['file_path'].name}")

        # Print implementation steps with sub-specs
        for step in spec.implementation:
            if step.sub_spec_id:
                print(f"{'  ' * (indent + 1)}🔗 {step.task} → {step.sub_spec_id[:8]}")

        # Recursively print children
        for child_id in spec_data["children"]:
            print_spec_tree(child_id, indent + 1)

    # Print each root spec tree
    for root_id in root_specs:
        print_spec_tree(root_id)
        print()

    # Print orphaned specs (have parent but parent not found)
    orphaned = [
        spec_id
        for spec_id, data in spec_graph.items()
        if data["parent"] and data["parent"] not in spec_graph
    ]

    if orphaned:
        print("🔗 Orphaned specs (parent not found):")
        for spec_id in orphaned:
            print(f"  ❓ {spec_id[:8]} (parent: {spec_graph[spec_id]['parent'][:8]})")


def get_spec_stats(specs_dir: Path) -> dict[str, Any]:
    """Get statistics about the specification graph."""

    generator = SpecGenerator(Path("templates"), specs_dir)
    spec_graph = generator.get_spec_graph()

    total_specs = len(spec_graph)
    root_specs = len([s for s in spec_graph.values() if not s["parent"]])
    leaf_specs = len([s for s in spec_graph.values() if not s["children"]])

    # Count by status
    status_counts = {}
    for spec_data in spec_graph.values():
        status = spec_data["spec"].metadata.status
        status_counts[status] = status_counts.get(status, 0) + 1

    # Calculate depth
    def get_depth(spec_id: str, visited: set = None) -> int:
        if visited is None:
            visited = set()
        if spec_id in visited or spec_id not in spec_graph:
            return 0

        visited.add(spec_id)
        max_child_depth = 0
        for child_id in spec_graph[spec_id]["children"]:
            max_child_depth = max(max_child_depth, get_depth(child_id, visited.copy()))

        return 1 + max_child_depth

    max_depth = max([get_depth(spec_id) for spec_id in spec_graph.keys()], default=0)

    return {
        "total_specs": total_specs,
        "root_specs": root_specs,
        "leaf_specs": leaf_specs,
        "max_depth": max_depth,
        "status_counts": status_counts,
    }
