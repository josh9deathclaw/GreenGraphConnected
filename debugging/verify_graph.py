import pickle
import networkx as nx
import os
import logging
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_integration import COMBINED_GRAPH_PATH, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def load_graph():
    logger.info(f"Loading graph from {COMBINED_GRAPH_PATH}...")
    with open(COMBINED_GRAPH_PATH, 'rb') as f:
        G = pickle.load(f)
    logger.info(f"✅ Loaded: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G

def verify_nodes(G):
    logger.info("\n🔍 Checking node attributes...")
    missing_latlon = [n for n, d in G.nodes(data=True) if 'lat' not in d or 'lon' not in d]
    mode_types = {}

    for n, d in G.nodes(data=True):
        mode = d.get('mode', 'unknown')
        mode_types[mode] = mode_types.get(mode, 0) + 1

    logger.info(f"Node mode breakdown:")
    for mode, count in mode_types.items():
        logger.info(f"  {mode:<10}: {count:,}")

    logger.info(f"Nodes missing lat/lon: {len(missing_latlon):,}")
    if len(missing_latlon) < 10:
        logger.info(f"Examples: {missing_latlon}")

def verify_edges(G):
    logger.info("\n🔍 Checking edge attributes...")
    missing_distance = [e for e in G.edges(data=True) if 'distance' not in e[2]]
    missing_mode = [e for e in G.edges(data=True) if 'mode' not in e[2]]

    mode_counts = {}
    edge_types = {}

    for u, v, data in G.edges(data=True):
        mode = data.get('mode', 'unknown')
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

        edge_type = data.get('edge_type', 'standard')
        edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

    logger.info(f"Edge mode breakdown:")
    for mode, count in mode_counts.items():
        logger.info(f"  {mode:<10}: {count:,}")

    logger.info(f"Edge type breakdown:")
    for e_type, count in edge_types.items():
        logger.info(f"  {e_type:<15}: {count:,}")

    logger.info(f"Edges missing distance: {len(missing_distance):,}")
    logger.info(f"Edges missing mode: {len(missing_mode):,}")

def check_connectivity(G):
    logger.info("\n🔍 Checking graph connectivity...")
    if nx.is_connected(G.to_undirected()):
        logger.info("✅ Graph is fully connected.")
    else:
        components = nx.number_connected_components(G.to_undirected())
        logger.warning(f"⚠️ Graph is NOT fully connected — {components} components found.")
        largest_cc = max(nx.connected_components(G.to_undirected()), key=len)
        logger.info(f"Largest component: {len(largest_cc):,} nodes")

def main():
    logger.info("="*60)
    logger.info("GRAPH INTEGRITY CHECK")
    logger.info("="*60)

    G = load_graph()
    verify_nodes(G)
    verify_edges(G)
    check_connectivity(G)

    logger.info("\n✅ Verification complete.\n")

if __name__ == "__main__":
    main()