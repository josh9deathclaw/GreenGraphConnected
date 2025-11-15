import networkx as nx
import pickle
import os
import sys

# ============================================================
# SETUP
# ============================================================
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_integration import COMBINED_GRAPH_PATH

# Load the graph
with open(COMBINED_GRAPH_PATH, 'rb') as f:
    G_combined = pickle.load(f)

# Test if walking edges between PT nodes exist in combined graph
walking_edges_found = 0
for u, v, data in G_combined.edges(data=True):
    if (data.get('mode') == 'walk' and 
        data.get('edge_type') == 'pt_transfer' and
        not u.startswith('road_') and 
        not v.startswith('road_')):
        walking_edges_found += 1

print(f"PT-to-PT walking edges in combined graph: {walking_edges_found}")

# Test if walking paths exist between your specific candidate nodes
start_candidates = ['pt_46882', 'pt_20569', 'pt_20567', 'pt_20566', 'pt_20570']
dest_candidates = ['pt_20562', 'pt_20563', 'pt_19450', 'pt_20561', 'pt_19302']

print("Testing walking paths between specific candidates:")
for start in start_candidates:
    for dest in dest_candidates:
        if G_combined.has_edge(start, dest):
            edge_data = G_combined[start][dest]
            if edge_data.get('mode') == 'walk':
                print(f"✅ DIRECT walking edge: {start} -> {dest}")
        
        # Check if any path exists (not just direct edge)
        try:
            path = nx.shortest_path(G_combined, start, dest, weight='time')
            print(f"✅ PATH exists: {start} -> {dest} (via {len(path)} nodes)")
        except nx.NetworkXNoPath:
            print(f"❌ NO PATH: {start} -> {dest}")
        except Exception as e:
            print(f"⚠️ ERROR: {start} -> {dest}: {e}")

# Get all PT nodes
pt_nodes = [n for n in G_combined.nodes() if not str(n).startswith('road_')]

# Create subgraph of just PT nodes and walking edges
pt_subgraph = G_combined.subgraph(pt_nodes).copy()
walking_edges = [(u, v) for u, v, d in pt_subgraph.edges(data=True) if d.get('mode') == 'walk']
pt_walking_graph = pt_subgraph.edge_subgraph(walking_edges)

print(f"PT walking network: {pt_walking_graph.number_of_nodes()} nodes, {pt_walking_graph.number_of_edges()} edges")
print(f"Connected components: {nx.number_connected_components(pt_walking_graph.to_undirected())}")

# Count how many walking edges are bidirectional
bidirectional_count = 0
for u, v, data in G_combined.edges(data=True):
    if (data.get('mode') == 'walk' and 
        data.get('edge_type') == 'pt_transfer' and
        G_combined.has_edge(v, u)):
        bidirectional_count += 1

print(f"Bidirectional walking edges: {bidirectional_count}")

# Test the specific candidate nodes again
start_candidates = ['pt_46882', 'pt_20569', 'pt_20567', 'pt_20566', 'pt_20570']
dest_candidates = ['pt_20562', 'pt_20563', 'pt_19450', 'pt_20561', 'pt_19302']

print("Testing walking paths between specific candidates:")
paths_found = 0
for start in start_candidates:
    for dest in dest_candidates:
        try:
            path = nx.shortest_path(G_combined, start, dest, weight='time')
            print(f"✅ PATH exists: {start} -> {dest}")
            paths_found += 1
        except nx.NetworkXNoPath:
            print(f"❌ NO PATH: {start} -> {dest}")

print(f"\nTotal paths found: {paths_found}/25")

# Check bidirectionality for different transport modes
print("Checking bidirectionality by mode:")
modes_to_check = ['tram', 'bus', 'train']

for mode in modes_to_check:
    mode_edges = []
    bidirectional_count = 0
    
    # Count edges for this mode
    for u, v, data in G_combined.edges(data=True):
        if data.get('mode') == mode:
            mode_edges.append((u, v))
    
    # Check bidirectionality
    for u, v in mode_edges:
        if G_combined.has_edge(v, u):
            bidirectional_count += 1
    
    print(f"  {mode}: {len(mode_edges)} edges, {bidirectional_count} bidirectional ({bidirectional_count/len(mode_edges)*100:.1f}%)")

# Also check specific tram/bus routes
print("\nChecking specific transport routes:")
transport_edges_found = 0
for u, v, data in G_combined.edges(data=True):
    if data.get('mode') in ['tram', 'bus', 'train']:
        transport_edges_found += 1
        if not G_combined.has_edge(v, u):
            print(f"  ❌ UNIDIRECTIONAL: {u} --[{data.get('mode')}]--> {v}")
        else:
            reverse_data = G_combined[v][u]
            if reverse_data.get('mode') == data.get('mode'):
                print(f"  ✅ BIDIRECTIONAL: {u} <--[{data.get('mode')}]--> {v}")

print(f"\nTotal transport edges found: {transport_edges_found}")