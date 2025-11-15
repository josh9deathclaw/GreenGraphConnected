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
    G = pickle.load(f)

print(f"📊 Original graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
print(f"📋 Graph type: {type(G)}")

# ============================================================
# NODE COMPATIBILITY FUNCTION
# ============================================================
def is_node_compatible(node, mode_filter=None):
    """
    Check if a node is compatible with the given mode filter
    """
    if mode_filter is None:
        return True
    
    # Check node type compatibility with STRICTER logic
    if node.startswith('road_'):
        # Road nodes ONLY for car mode (not for walking between public transport)
        return 'car' in mode_filter
    elif node.startswith('train_'):
        return 'train' in mode_filter
    elif node.startswith('tram_'):
        return 'tram' in mode_filter
    elif node.startswith('bus_'):
        return 'bus' in mode_filter
    elif node.startswith('pt_'):  # Public transport nodes
        # PT nodes should work with any public transport mode
        return any(mode in mode_filter for mode in ['train', 'tram', 'bus', 'walk'])
    
    # Default: allow unknown node types
    return True

# ============================================================
# FIXED FILTER GRAPH FUNCTION
# ============================================================
def filter_graph_by_modes(graph, enabled_modes):
    """
    Filter graph to only include edges with allowed transport modes
    """
    filtered_graph = nx.Graph() if isinstance(graph, nx.Graph) else nx.MultiDiGraph()
    
    # Add compatible nodes
    for node, data in graph.nodes(data=True):
        if is_node_compatible(node, enabled_modes):
            filtered_graph.add_node(node, **data)
    
    # Add compatible edges (handle both Graph and MultiGraph)
    if hasattr(graph, 'edges'):
        # For MultiGraph
        if hasattr(graph, 'is_multigraph') and graph.is_multigraph():
            for u, v, key, data in graph.edges(keys=True, data=True):
                if u in filtered_graph and v in filtered_graph:
                    edge_mode = data.get('mode', '')
                    if edge_mode in enabled_modes:
                        filtered_graph.add_edge(u, v, key=key, **data)
        else:
            # For regular Graph
            for u, v, data in graph.edges(data=True):
                if u in filtered_graph and v in filtered_graph:
                    edge_mode = data.get('mode', '')
                    if edge_mode in enabled_modes:
                        filtered_graph.add_edge(u, v, **data)
    
    return filtered_graph

# ============================================================
# TEST DIFFERENT MODE COMBINATIONS
# ============================================================
test_cases = [
    ['car', 'walk', 'train', 'tram', 'bus'],  # All modes
    ['walk', 'train', 'tram', 'bus'],         # No car
    ['train', 'tram', 'bus'],                 # Only public transport
    ['walk'],                                 # Only walking
    ['car']                                   # Only car
]

for modes in test_cases:
    print(f"\n🔧 Testing modes: {modes}")
    
    # Filter the graph
    filtered = filter_graph_by_modes(G, modes)
    print(f"   Filtered: {filtered.number_of_nodes()} nodes, {filtered.number_of_edges()} edges")
    
    # Count nodes by type
    node_types = {}
    for node in filtered.nodes():
        if node.startswith('road_'): node_types['road'] = node_types.get('road', 0) + 1
        elif node.startswith('train_'): node_types['train'] = node_types.get('train', 0) + 1
        elif node.startswith('tram_'): node_types['tram'] = node_types.get('tram', 0) + 1
        elif node.startswith('bus_'): node_types['bus'] = node_types.get('bus', 0) + 1
        else: node_types['other'] = node_types.get('other', 0) + 1
    
    print(f"   Node types: {node_types}")
    
    # Test specific paths
    test_paths = [
        ('train_vic:rail:GFE', 'train_vic:rail:ECM'),
        ('train_vic:rail:GFE', 'road_311436148'),
        ('road_518305545', 'road_311407187')
    ]
    
    for start, end in test_paths:
        if start in filtered and end in filtered:
            try:
                path_exists = nx.has_path(filtered, start, end)
                print(f"   {start} → {end}: {'✅' if path_exists else '❌'} Path exists")
            except:
                print(f"   {start} → {end}: ⚠️ Error checking path")
        else:
            missing = []
            if start not in filtered: missing.append(start)
            if end not in filtered: missing.append(end)
            print(f"   {start} → {end}: ❌ Nodes missing: {missing}")

# ============================================================
# CHECK CANDIDATE NODES FOR SPECIFIC COORDINATES
# ============================================================
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate Haversine distance between two points in km"""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371  # Earth radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def find_candidate_nodes(lat, lon, mode_filter=None, max_distance_km=0.5, max_candidates=5):
    """Find candidate nodes for given coordinates"""
    candidates = []
    
    for node, data in G.nodes(data=True):
        if 'lat' not in data or 'lon' not in data:
            continue
        
        distance = haversine_distance(lat, lon, data['lat'], data['lon'])
        
        if distance <= max_distance_km:
            if is_node_compatible(node, mode_filter):
                candidates.append((node, distance))
    
    return sorted(candidates, key=lambda x: x[1])[:max_candidates]

print(f"\n📍 Testing candidate nodes for coordinates:")
test_coords = [
    (-37.8215, 145.0364),  # Your start coords
    (-37.8183396, 145.0487937)  # Your dest coords
]

for lat, lon in test_coords:
    print(f"\n   Coordinates: ({lat}, {lon})")
    for modes in [['car', 'walk', 'train', 'tram', 'bus'], ['walk', 'train', 'tram', 'bus']]:
        candidates = find_candidate_nodes(lat, lon, mode_filter=modes, max_distance_km=0.5)
        print(f"   Modes {modes}: {[node for node, dist in candidates]}")