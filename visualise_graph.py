"""
Static PNG Visualization of Multimodal Graph
Generates a 2D plotted image of the combined graph for documentation or reports.
"""

import os
import pickle
import networkx as nx
import matplotlib.pyplot as plt
import logging
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_integration import (
    COMBINED_GRAPH_PATH,
    STATIC_GRAPH_IMAGE,
    MODE_COLORS,
    LOG_LEVEL,
    LOG_FORMAT
)

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def load_combined_graph():
    """Load combined multimodal graph"""
    logger.info(f"Loading combined graph from {COMBINED_GRAPH_PATH}...")
    with open(COMBINED_GRAPH_PATH, 'rb') as f:
        G = pickle.load(f)
    logger.info(f"✅ Loaded: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G


def visualize_graph(G):
    """Plot multimodal network as static PNG"""
    logger.info("\nGenerating static PNG visualization...")

    # Prepare color map by edge mode
    mode_edges = {mode: [] for mode in MODE_COLORS.keys()}
    for u, v, data in G.edges(data=True):
        mode = data.get('mode', 'unknown')
        if mode not in MODE_COLORS:
            mode = 'walk'  # fallback
        mode_edges[mode].append((u, v))

    # Get coordinates
    pos = {n: (d['lon'], d['lat']) for n, d in G.nodes(data=True) if 'lat' in d and 'lon' in d}

    # Setup plot
    plt.figure(figsize=(12, 10))
    plt.axis('off')
    plt.title("Multimodal Transport Network (Burnley → Hawthorn → Box Hill)", fontsize=14, pad=20)

    # Draw by mode
    for mode, edges in mode_edges.items():
        if not edges:
            continue
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=edges,
            edge_color=MODE_COLORS[mode],
            alpha=0.6,
            width=1.2 if mode == 'car' else 0.8
        )

    # Draw train station nodes for visibility
    train_nodes = [
        n for n, d in G.nodes(data=True)
        if any(G[n][nbr].get('mode') == 'train' for nbr in G.neighbors(n))
    ]
    nx.draw_networkx_nodes(G, pos, nodelist=train_nodes, node_size=20, node_color='blue', label='Train Stations')

    plt.legend(handles=[
        plt.Line2D([0], [0], color=MODE_COLORS['car'], lw=2, label='Car'),
        plt.Line2D([0], [0], color=MODE_COLORS['train'], lw=2, label='Train'),
        plt.Line2D([0], [0], color=MODE_COLORS['tram'], lw=2, label='Tram'),
        plt.Line2D([0], [0], color=MODE_COLORS['bus'], lw=2, label='Bus'),
        plt.Line2D([0], [0], color=MODE_COLORS['walk'], lw=2, label='Walking')
    ], loc='lower left', fontsize=8)

    # Save PNG
    os.makedirs(os.path.dirname(STATIC_GRAPH_IMAGE), exist_ok=True)
    plt.savefig(STATIC_GRAPH_IMAGE, dpi=300, bbox_inches='tight')
    logger.info(f"✅ Saved static graph image: {STATIC_GRAPH_IMAGE}")
    plt.close()


def main():
    G = load_combined_graph()
    visualize_graph(G)


if __name__ == "__main__":
    main()
