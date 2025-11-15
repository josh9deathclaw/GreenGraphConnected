import networkx as nx
import pickle
import os

# Test on the PT graph directly (before merging)
with open('data/graphs/pt_graph.gpickle', 'rb') as f:
    G_pt = pickle.load(f)

print("Checking PT graph (before merging):")
pt_walking_edges = []
for u, v, data in G_pt.edges(data=True):
    if data.get('mode') == 'walk' and data.get('edge_type') == 'pt_transfer':
        pt_walking_edges.append((u, v))

print(f"PT graph walking edges: {len(pt_walking_edges)}")

# Check bidirectionality in PT graph
bidirectional_in_pt = 0
for u, v in pt_walking_edges:
    if G_pt.has_edge(v, u):
        bidirectional_in_pt += 1

print(f"Bidirectional in PT graph: {bidirectional_in_pt}")
print(f"Should be: {len(pt_walking_edges)} (all edges should be bidirectional)")
