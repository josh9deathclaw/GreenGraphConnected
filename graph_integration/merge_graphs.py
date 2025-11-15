#Merge PT and Car Graphs into Combined Multimodal Graph
import networkx as nx
import pickle
import json
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_integration import (
    PT_GRAPH_PATH, CAR_GRAPH_PATH, COMBINED_GRAPH_PATH,
    OUTPUT_DIR, WALKING_SPEED, LOG_LEVEL, LOG_FORMAT
)


logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

CONNECTIONS_JSON = f'{OUTPUT_DIR}/connections.json'

def load_graphs():
    """Load PT and Car graphs"""
    logger.info("Loading graphs...")
    
    # Load PT graph (with walking connections)
    logger.info(f"  PT graph from {PT_GRAPH_PATH}...")
    with open(PT_GRAPH_PATH, 'rb') as f:
        G_pt = pickle.load(f)
    logger.info(f"  ✅ PT: {G_pt.number_of_nodes():,} nodes, {G_pt.number_of_edges():,} edges")
    
    # Load Car graph
    logger.info(f"  Car graph from {CAR_GRAPH_PATH}...")
    with open(CAR_GRAPH_PATH, 'rb') as f:
        G_car = pickle.load(f)
    logger.info(f"  ✅ Car: {G_car.number_of_nodes():,} nodes, {G_car.number_of_edges():,} edges")
    
    return G_pt, G_car


def load_connections():
    """Load car-to-PT connection data"""
    logger.info(f"\nLoading connections from {CONNECTIONS_JSON}...")
    
    with open(CONNECTIONS_JSON, 'r') as f:
        connections = json.load(f)
    
    logger.info(f"✅ Loaded {len(connections)} car-to-PT connections")
    return connections


def create_combined_graph(G_pt, G_car, connections):
    """Merge graphs and add connection edges"""
    
    logger.info("\n" + "="*60)
    logger.info("CREATING COMBINED GRAPH")
    logger.info("="*60)
    
    # Create new directed graph
    G_combined = nx.DiGraph()
    
    # Add PT network
    logger.info("\nAdding PT network...")
    G_combined.add_nodes_from(G_pt.nodes(data=True))
    G_combined.add_edges_from(G_pt.edges(data=True))
    logger.info(f"  ✅ Added {G_pt.number_of_nodes():,} PT nodes")
    logger.info(f"  ✅ Added {G_pt.number_of_edges():,} PT edges")

    # FIX: Ensure bidirectionality for walking edges
    logger.info("\n🔄 Ensuring bidirectionality for walking edges...")
    walking_edges_added = 0
    for u, v, data in G_pt.edges(data=True):
        if (data.get('mode') == 'walk' and 
            data.get('edge_type') == 'pt_transfer' and
            not G_combined.has_edge(v, u)):  # If reverse edge doesn't exist
            # Add the reverse edge
            G_combined.add_edge(v, u, **data)
            walking_edges_added += 1

    print("Adding reverse edges for transport modes...")
    reverse_edges_added = 0

    for u, v, data in G_combined.edges(data=True):
        if data.get('mode') in ['tram', 'bus', 'train']:
            # If reverse edge doesn't exist, add it
            if not G_combined.has_edge(v, u):
                # Create reverse edge with same attributes
                G_combined.add_edge(v, u, **data)
                reverse_edges_added += 1

    print(f"✅ Added {reverse_edges_added} reverse transport edges")

    logger.info(f"  ✅ Added {walking_edges_added} reverse walking edges")

    # DEBUG: Check bidirectionality right after adding PT edges
    logger.info("\n🔍 DEBUG: Checking PT walking edges in combined graph...")
    pt_walking_in_combined = 0
    bidirectional_in_combined = 0

    for u, v, data in G_combined.edges(data=True):
        if (data.get('mode') == 'walk' and 
            data.get('edge_type') == 'pt_transfer' and
            not u.startswith('road_') and 
            not v.startswith('road_')):
            pt_walking_in_combined += 1
            if G_combined.has_edge(v, u):
                bidirectional_in_combined += 1
    
    logger.info(f"  PT walking edges in combined: {pt_walking_in_combined}")
    logger.info(f"  Bidirectional in combined: {bidirectional_in_combined}")
    logger.info(f"  Expected: {22792} bidirectional edges")
    
    # Add Car network
    logger.info("\nAdding car network...")
    G_combined.add_nodes_from(G_car.nodes(data=True))
    G_combined.add_edges_from(G_car.edges(data=True))
    logger.info(f"  ✅ Added {G_car.number_of_nodes():,} car nodes")
    logger.info(f"  ✅ Added {G_car.number_of_edges():,} car edges")
    
    # Add ONE-WAY connection edges (car → PT only)
    logger.info("\nAdding car-to-PT connection edges (ONE-WAY)...")
    
    connections_added = 0
    for conn in connections:
        road_node = conn['road_node']
        station_id = conn['station_id']
        distance = conn['distance']
        walk_time = conn['walk_time']
        
        # Add ONE-WAY edge: road → station
        G_combined.add_edge(
            road_node,
            station_id,
            mode='walk',
            distance=distance,
            time=walk_time,
            emissions=0,
            edge_type='car_to_pt_transfer',
            station_name=conn['station_name']
        )
        
        connections_added += 1
    
    logger.info(f"  ✅ Added {connections_added} one-way connection edges (car→PT)")
    
    return G_combined


def analyze_combined_graph(G):
    """Analyze the combined graph"""
    
    logger.info("\n" + "="*60)
    logger.info("COMBINED GRAPH ANALYSIS")
    logger.info("="*60)
    
    logger.info(f"\nTotal nodes: {G.number_of_nodes():,}")
    logger.info(f"Total edges: {G.number_of_edges():,}")
    
    # Count by mode
    mode_counts = {}
    for u, v, data in G.edges(data=True):
        mode = data.get('mode', 'unknown')
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    
    logger.info("\nEdges by mode:")
    for mode, count in sorted(mode_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {mode:10s}: {count:,}")
    
    # Check connectivity
    if isinstance(G, nx.DiGraph):
        weak_components = nx.number_weakly_connected_components(G)
        logger.info(f"\nWeakly connected components: {weak_components}")
        
        if weak_components == 1:
            logger.info("✅ Graph is fully connected!")
        else:
            logger.warning(f"⚠️  Graph has {weak_components} separate components")

    pt_nodes = [n for n in G.nodes if not str(n).startswith('road_')]
    logger.info(f"PT nodes detected: {len(pt_nodes)}")


def test_multimodal_path(G):
    """Test that multimodal routing works"""
    
    logger.info("\n" + "="*60)
    logger.info("MULTIMODAL PATH TEST")
    logger.info("="*60)
    
    # Find a car node and a PT node
    car_nodes = [n for n in G.nodes() if str(n).startswith('road_')]
    pt_nodes = [n for n in G.nodes() if not str(n).startswith('road_')]
    
    if not car_nodes or not pt_nodes:
        logger.warning("Cannot test - missing nodes")
        return
    
    source = car_nodes[100]  # Random car node
    target = pt_nodes[100]   # Random PT node
    
    logger.info(f"Testing path from car node to PT node...")
    logger.info(f"  Source: {source}")
    logger.info(f"  Target: {target}")
    
    try:
        path = nx.shortest_path(G, source, target, weight='time')
        logger.info(f"\n✅ Multimodal path found!")
        logger.info(f"   Path length: {len(path)} nodes")
        
        # Analyze path
        modes_used = []
        for i in range(len(path)-1):
            mode = G[path[i]][path[i+1]].get('mode', 'unknown')
            if not modes_used or modes_used[-1] != mode:
                modes_used.append(mode)
        
        logger.info(f"   Modes used: {' → '.join(modes_used)}")
        
        # Show first few hops
        logger.info("\n   Path preview:")
        for i in range(min(5, len(path)-1)):
            u, v = path[i], path[i+1]
            mode = G[u][v].get('mode')
            logger.info(f"      {u} --[{mode}]--> {v}")
        
        if len(path) > 5:
            logger.info(f"      ... and {len(path)-5} more hops")
        
    except nx.NetworkXNoPath:
        logger.error("❌ No path found between test nodes")
    except Exception as e:
        logger.error(f"❌ Error testing path: {e}")


def save_combined_graph(G):
    """Save the combined graph"""
    
    logger.info(f"\n💾 Saving combined graph to {COMBINED_GRAPH_PATH}...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(COMBINED_GRAPH_PATH, 'wb') as f:
        pickle.dump(G, f)
    
    logger.info("✅ Saved")


def main():
    """Main execution"""
    
    logger.info("="*60)
    logger.info("GRAPH MERGING")
    logger.info("="*60)
    
    # Load graphs
    G_pt, G_car = load_graphs()
    
    # Load connections
    connections = load_connections()
    
    # Create combined graph
    G_combined = create_combined_graph(G_pt, G_car, connections)
    
    # Analyze
    analyze_combined_graph(G_combined)
    
    # Test routing
    test_multimodal_path(G_combined)
    
    # Save
    save_combined_graph(G_combined)
    
    logger.info("\n" + "="*60)
    logger.info("✅ GRAPH MERGING COMPLETE")
    logger.info("="*60)
    logger.info(f"\nCombined graph: {COMBINED_GRAPH_PATH}")
    logger.info(f"Nodes: {G_combined.number_of_nodes():,}")
    logger.info(f"Edges: {G_combined.number_of_edges():,}")
    logger.info("\nNext step:")
    logger.info("  Run: python 5_visualize_combined.py")


if __name__ == "__main__":
    main()