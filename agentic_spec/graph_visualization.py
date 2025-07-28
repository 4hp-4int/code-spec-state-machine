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


def visualize_spec_graph(
    specs_dir: Path, output_file: str = "spec_graph.png", show_tasks: bool = False
):
    """Create a visual graph of specification relationships.

    Args:
        specs_dir: Directory containing specifications
        output_file: Output file path for the graph image
        show_tasks: Whether to include task nodes in the graph
    """

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
    graph = nx.DiGraph()

    # Add specification nodes
    for spec_id, spec_data in spec_graph.items():
        spec = spec_data["spec"]
        tasks_count = len(spec.implementation)
        graph.add_node(
            spec_id,
            label=f"{spec_id[:8]}\n{spec.metadata.title[:20]}...\n({tasks_count} tasks)",
            node_type="spec",
            status=spec.metadata.status,
        )

    # Add task nodes if requested
    if show_tasks:
        for spec_id, spec_data in spec_graph.items():
            spec = spec_data["spec"]
            for i, step in enumerate(spec.implementation):
                task_id = f"{spec_id}:{i}"
                graph.add_node(
                    task_id,
                    label=f"Task {i}\n{step.task[:30]}...",
                    node_type="task",
                    has_subspec=bool(step.sub_spec_id),
                )
                # Edge from spec to its tasks
                graph.add_edge(spec_id, task_id, edge_type="has_task")

                # Edge from task to sub-spec if exists
                if step.sub_spec_id and step.sub_spec_id in spec_graph:
                    graph.add_edge(task_id, step.sub_spec_id, edge_type="implements")

    # Add edges (parent -> child relationships)
    for spec_id, spec_data in spec_graph.items():
        parent_id = spec_data["parent"]
        if parent_id and parent_id in spec_graph:
            graph.add_edge(parent_id, spec_id, edge_type="parent_child")

    # Set up the plot
    plt.figure(figsize=(16, 12))

    # Use hierarchical layout if possible
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except:
        # Fallback to spring layout
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

    # Separate nodes by type
    spec_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "spec"]
    task_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "task"]

    # Color specs by status
    status_colors = {
        "draft": "lightblue",
        "reviewed": "yellow",
        "approved": "lightgreen",
        "implemented": "darkgreen",
    }

    spec_colors = [
        status_colors.get(G.nodes[node].get("status", "draft"), "lightgray")
        for node in spec_nodes
    ]

    # Draw specification nodes
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=spec_nodes,
        node_color=spec_colors,
        node_size=3000,
        node_shape="s",  # Square for specs
        alpha=0.9,
    )

    # Draw task nodes if present
    if task_nodes:
        task_colors = [
            "lightcoral" if G.nodes[n].get("has_subspec") else "lightyellow"
            for n in task_nodes
        ]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=task_nodes,
            node_color=task_colors,
            node_size=1500,
            node_shape="o",  # Circle for tasks
            alpha=0.7,
        )

    # Draw edges with different styles
    edge_types = {
        "parent_child": {"color": "blue", "style": "solid", "width": 2},
        "has_task": {"color": "gray", "style": "dotted", "width": 1},
        "implements": {"color": "green", "style": "dashed", "width": 1.5},
    }

    for edge_type, style in edge_types.items():
        edges = [
            (u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == edge_type
        ]
        if edges:
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=edges,
                edge_color=style["color"],
                style=style["style"],
                width=style["width"],
                arrows=True,
                arrowsize=15,
                alpha=0.6,
            )

    # Draw labels
    labels = {node: data["label"] for node, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight="bold")

    plt.title(
        "Specification and Task Relationship Graph", fontsize=16, fontweight="bold"
    )

    # Add legend
    legend_elements = [
        plt.Line2D(
            [0],
            [0],
            marker="s",
            color="w",
            markerfacecolor=color,
            markersize=10,
            label=status.title(),
        )
        for status, color in status_colors.items()
    ]

    if show_tasks:
        legend_elements.extend(
            [
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="lightyellow",
                    markersize=10,
                    label="Task",
                ),
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="lightcoral",
                    markersize=10,
                    label="Task with Sub-spec",
                ),
            ]
        )

    plt.legend(handles=legend_elements, loc="upper right")

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Graph visualization saved to {output_file}")
    plt.show()


def print_spec_graph(specs_dir: Path | str, show_tasks: bool = False):
    """Print a text-based representation of the specification graph.

    Args:
        specs_dir: Directory containing specifications
        show_tasks: Whether to show individual tasks within specs
    """

    # Convert to Path if string
    specs_dir_path = Path(specs_dir) if isinstance(specs_dir, str) else specs_dir
    generator = SpecGenerator(Path("templates"), specs_dir_path)
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
        for i, step in enumerate(spec.implementation):
            if show_tasks or step.sub_spec_id:
                task_prefix = "  " * (indent + 1) + f"├─ Task {i}: "
                if step.sub_spec_id:
                    print(f"{task_prefix}🔗 {step.task} → {step.sub_spec_id[:8]}")
                elif show_tasks:
                    print(f"{task_prefix}📋 {step.task}")

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


def print_task_tree(specs_dir: Path | str, spec_id: str):
    """Print a detailed task tree for a specific specification.

    Shows all tasks and their sub-specifications in a hierarchical view.

    Args:
        specs_dir: Directory containing specifications
        spec_id: ID of the specification to show task tree for
    """
    # Convert to Path if string
    specs_dir_path = Path(specs_dir) if isinstance(specs_dir, str) else specs_dir
    generator = SpecGenerator(Path("templates"), specs_dir_path)
    spec_graph = generator.get_spec_graph()

    if spec_id not in spec_graph:
        print(f"❌ Specification {spec_id} not found")
        return

    print(f"📋 Task Tree for Specification: {spec_id}")
    print("=" * 60)

    def print_tasks_recursive(
        current_spec_id: str, indent: int = 0, task_path: str = ""
    ):
        """Recursively print tasks and their sub-specifications."""
        if current_spec_id not in spec_graph:
            return

        spec_data = spec_graph[current_spec_id]
        spec = spec_data["spec"]

        # Print spec header if not root
        if indent > 0:
            prefix = "│  " * (indent - 1) + "└─ "
            print(
                f"{prefix}📦 Sub-spec: {current_spec_id[:8]} - {spec.metadata.title[:50]}..."
            )

        # Print tasks for this spec
        for i, step in enumerate(spec.implementation):
            task_num = f"{task_path}{i}" if task_path else str(i)
            task_prefix = "│  " * indent + f"├─ [{task_num}] "

            # Check if task has progress in database
            progress_emoji = "⏳"  # Default pending
            if hasattr(step, "progress") and step.progress:
                status = (
                    step.progress.status.value
                    if hasattr(step.progress.status, "value")
                    else str(step.progress.status)
                )
                progress_emoji = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "blocked": "🚫",
                    "approved": "✓",
                    "rejected": "❌",
                }.get(status, "⏳")

            print(f"{task_prefix}{progress_emoji} {step.task}")

            # If this task has a sub-specification, recurse
            if step.sub_spec_id:
                print_tasks_recursive(step.sub_spec_id, indent + 1, f"{task_num}.")

    # Start with the root spec
    root_spec = spec_graph[spec_id]["spec"]
    print(f"🎯 Root: {root_spec.metadata.title}")
    print(f"👤 Author: {root_spec.metadata.author or 'N/A'}")
    print(f"📊 Status: {root_spec.metadata.status}")
    print()

    print_tasks_recursive(spec_id)

    # Print summary statistics
    print("\n📊 Summary:")
    total_tasks = 0
    total_with_subspecs = 0

    def count_tasks(current_spec_id: str):
        nonlocal total_tasks, total_with_subspecs
        if current_spec_id not in spec_graph:
            return
        spec = spec_graph[current_spec_id]["spec"]
        total_tasks += len(spec.implementation)
        for step in spec.implementation:
            if step.sub_spec_id:
                total_with_subspecs += 1
                count_tasks(step.sub_spec_id)

    count_tasks(spec_id)
    print(f"   Total Tasks: {total_tasks}")
    print(f"   Tasks with Sub-specs: {total_with_subspecs}")
    print("=" * 60)


def get_spec_stats(specs_dir: Path | str) -> dict[str, Any]:
    """Get statistics about the specification graph."""

    # Convert to Path if string
    specs_dir_path = Path(specs_dir) if isinstance(specs_dir, str) else specs_dir
    generator = SpecGenerator(Path("templates"), specs_dir_path)
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
    def get_depth(spec_id: str, visited: set | None = None) -> int:
        if visited is None:
            visited = set()
        if spec_id in visited or spec_id not in spec_graph:
            return 0

        visited.add(spec_id)
        max_child_depth = 0
        for child_id in spec_graph[spec_id]["children"]:
            max_child_depth = max(max_child_depth, get_depth(child_id, visited.copy()))

        return 1 + max_child_depth

    max_depth = max([get_depth(spec_id) for spec_id in spec_graph], default=0)

    return {
        "total_specs": total_specs,
        "root_specs": root_specs,
        "leaf_specs": leaf_specs,
        "max_depth": max_depth,
        "status_counts": status_counts,
    }


def detect_cycles(specs_dir: Path | str) -> list[list[str]]:
    """Detect cycles in the specification graph.

    Returns:
        List of cycles found, where each cycle is a list of spec IDs
    """
    specs_dir_path = Path(specs_dir) if isinstance(specs_dir, str) else specs_dir
    generator = SpecGenerator(Path("templates"), specs_dir_path)
    spec_graph = generator.get_spec_graph()

    if not spec_graph or not VISUALIZATION_AVAILABLE:
        return []

    # Build NetworkX graph
    G = nx.DiGraph()

    # Add all specs as nodes
    for spec_id in spec_graph:
        graph.add_node(spec_id)

    # Add edges for parent-child relationships
    for spec_id, spec_data in spec_graph.items():
        # Parent edges
        if spec_data["parent"] and spec_data["parent"] in spec_graph:
            graph.add_edge(spec_data["parent"], spec_id)

        # Sub-spec edges from tasks
        spec = spec_data["spec"]
        for step in spec.implementation:
            if step.sub_spec_id and step.sub_spec_id in spec_graph:
                graph.add_edge(spec_id, step.sub_spec_id)

    # Find cycles
    try:
        cycles = list(nx.simple_cycles(G))
        return cycles
    except:
        return []
