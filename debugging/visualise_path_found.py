import networkx as nx
import folium
import logging
import pickle
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(message)s")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_integration import COMBINED_GRAPH_PATH

GRAPH_PATH = "data/graphs/merged_graph.gpickle"
with open(COMBINED_GRAPH_PATH, 'rb') as f:
        G = pickle.load(f)
logging.info(f"✅ Loaded graph with {len(G.nodes())} nodes, {len(G.edges())} edges")

def visualize_path(G, path, filename="specific_route.html"):
    # Try to extract lat/lon from node attributes
    coords = []
    for node in path:
        ndata = G.nodes[node]
        lat, lon = ndata.get("lat"), ndata.get("lon")
        if lat and lon:
            coords.append((lat, lon))
    
    if not coords:
        logging.warning("⚠️ No coordinates found in nodes — cannot plot.")
        return

    m = folium.Map(location=coords[0], zoom_start=14)
    
    # Add path as polyline
    folium.PolyLine(coords, color="green", weight=5, opacity=0.8).add_to(m)
    
    # Add markers for start and end
    folium.Marker(coords[0], popup="Start", icon=folium.Icon(color="blue")).add_to(m)
    folium.Marker(coords[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)
    
    m.save(filename)
    logging.info(f"🗺️ Route visual saved as {filename}")

while True:
    print("\n=== PATH FINDER ===")
    start = input("Enter START node ID (or 'exit' to quit): ").strip()
    if start.lower() == "exit":
        break
    end = input("Enter END node ID: ").strip()
    mode = input("Type of route ('shortest' or 'greenest'): ").strip().lower()

    if start not in G or end not in G:
        print("❌ Node not found.")
        continue

    try:
        if mode == "greenest":
            weight = "emissions"
            # create cost if not already defined
            for u, v, data in G.edges(data=True):
                if "green_cost" not in data:
                    data["green_cost"] = 1 / (data.get("green_score", 1e-6))
        else:
            weight = "length"

        path = nx.shortest_path(G, start, end, weight=weight)
        total = nx.shortest_path_length(G, start, end, weight=weight)

        print(f"\n✅ Path found ({mode}): total cost = {total:.2f}")
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            data = G[u][v]
            mode = data.get("mode", "?")
            cost = data.get(weight, "?")
            print(f"{u} --[{mode}, {cost}]--> {v}")

        visualize_path(G, path)

    except nx.NetworkXNoPath:
        print("❌ No path found.")
