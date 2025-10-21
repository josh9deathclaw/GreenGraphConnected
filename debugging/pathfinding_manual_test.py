import networkx as nx
import logging
import sys
import pickle
import os
# ============================================================
# SETUP LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ============================================================
# LOAD GRAPH
# ============================================================

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_integration import COMBINED_GRAPH_PATH, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

with open(COMBINED_GRAPH_PATH, 'rb') as f:
        G = pickle.load(f)

logging.info(f"✅ Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# ============================================================
# MAIN INTERACTIVE LOOP
# ============================================================
while True:
    print("\n============================================================")
    source = input("Enter SOURCE node ID (or 'q' to quit): ").strip()
    if source.lower() == "q":
        break

    target = input("Enter TARGET node ID: ").strip()
    if target.lower() == "q":
        break

    if source not in G or target not in G:
        print("❌ One or both nodes not found in graph.")
        continue

    print("\nFinding path...")
    try:
        path = nx.shortest_path(G, source=source, target=target, weight="weight")
        total_weight = nx.shortest_path_length(G, source=source, target=target, weight="weight")

        print("\n✅ Path found!")
        print(f"→ Path length (weighted): {total_weight:.2f}")
        print(f"→ Number of hops: {len(path) - 1}\n")

        # Display a compact summary of the path
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = G[u][v]
            mode = edge_data.get("mode", "unknown")

            # Some edges (like connection edges) might not have 'weight'
            weight = edge_data.get("weight", None)
            if isinstance(weight, (int, float)):
                weight_str = f"{weight:.1f}"
            else:
                weight_str = "?"

            print(f"{u} --[{mode}, {weight_str}]--> {v}")

    except nx.NetworkXNoPath:
        print("❌ No path found between those nodes.")
    except Exception as e:
        print(f"⚠️ Error: {e}")

print("\n👋 Exiting pathfinder.")