import pickle
import networkx as nx
import random
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_integration import COMBINED_GRAPH_PATH, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def load_graph():
    with open(COMBINED_GRAPH_PATH, 'rb') as f:
        G = pickle.load(f)
    logger.info(f"✅ Loaded: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G

def test_random_paths(G, n_tests=5):
    logger.info(f"\n🚦 Running {n_tests} random pathfinding tests...")

    nodes = list(G.nodes())
    for i in range(n_tests):
        src, dst = random.sample(nodes, 2)
        try:
            path = nx.shortest_path(G, src, dst, weight='time')
            total_time = sum(G[u][v].get('time', 0) for u, v in zip(path[:-1], path[1:]))
            modes_used = set(G[u][v].get('mode', 'unknown') for u, v in zip(path[:-1], path[1:]))
            logger.info(f"Path {i+1}: {src} → {dst}")
            logger.info(f"  Length: {len(path)} hops")
            logger.info(f"  Total time: {total_time/60:.1f} min")
            logger.info(f"  Modes used: {', '.join(modes_used)}\n")
        except nx.NetworkXNoPath:
            logger.warning(f"⚠️ No path between {src} and {dst}")

def test_specific_path(G, src, dst):
    """Test a known path (for example Burnley → Box Hill)"""
    logger.info(f"\n🧭 Testing specific path: {src} → {dst}")
    try:
        path = nx.shortest_path(G, src, dst, weight='time')
        logger.info(f"✅ Found path ({len(path)} steps)")
        for i, (u, v) in enumerate(zip(path[:-1], path[1:])):
            edge = G[u][v]
            logger.info(f"  {i+1}. {u} → {v} [{edge.get('mode')}] {edge.get('distance', 0):.1f}m")
    except nx.NetworkXNoPath:
        logger.warning("⚠️ No path found!")

def main():
    logger.info("="*60)
    logger.info("PATHFINDING VERIFICATION")
    logger.info("="*60)

    G = load_graph()
    test_random_paths(G)
    # Replace with known nodes from your corridor
    # test_specific_path(G, "burnley_station_id", "box_hill_station_id")

    logger.info("\n✅ Pathfinding tests complete.\n")

if __name__ == "__main__":
    main()