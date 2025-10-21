import networkx as nx
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

with open(COMBINED_GRAPH_PATH, 'rb') as f:
        G = pickle.load(f)

print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")

modes = {}
for _, data in G.nodes(data=True):
    mode = data.get("mode", "unknown")
    modes[mode] = modes.get(mode, 0) + 1

print("Node modes:", modes)
isolated = list(nx.isolates(G))
print(f"Isolated nodes: {len(isolated)}")

nodes = list(G.nodes)
for i in range(5):
    src, dst = random.sample(nodes, 2)
    try:
        path = nx.shortest_path(G, src, dst, weight="time")
        logging.info(f"✅ Path {i+1}: {src} → {dst} ({len(path)} hops)")
    except nx.NetworkXNoPath:
        logging.warning(f"⚠️ No path between {src} and {dst}")