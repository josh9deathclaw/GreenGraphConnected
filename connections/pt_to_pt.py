""""
Walking Connections between PT Stops
Bidirectional walking edges between nearby PT Stops

Simplification: only in region of train stations
"""

import networkx as nx
import pickle
from geopy.distance import geodesic
from scipy.spatial import KDTree
import numpy as np
import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_integration import (
    PT_GRAPH_PATH, OUTPUT_DIR,
    MAX_WALKING_DISTANCE_M, WALKING_SPEED,
    LOG_LEVEL, LOG_FORMAT
)


logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

class PTWalkingConnectionBuilder:
    """Builds walking connection edges between PT stops"""
    
    def __init__(self, graph, max_walk_distance=MAX_WALKING_DISTANCE_M):
        self.graph = graph
        self.max_walk_distance = max_walk_distance
        self.walking_speed = WALKING_SPEED
        
    def add_walking_edges(self):
        logger.info("="*60)
        logger.info("ADDING PT WALKING CONNECTIONS")
        logger.info("="*60)
        logger.info(f"Max walking distance: {self.max_walk_distance}m")

        # OPTION 2: Clear existing walking edges first
        logger.info("Clearing existing walking edges...")
        edges_to_remove = []
        for u, v, data in self.graph.edges(data=True):
            if data.get('mode') == 'walk' and data.get('edge_type') == 'pt_transfer':
                edges_to_remove.append((u, v))
        
        for u, v in edges_to_remove:
            self.graph.remove_edge(u, v)
        
        logger.info(f"✅ Removed {len(edges_to_remove)} existing walking edges")
        
        # Extract PT nodes with coordinates
        pt_nodes = self.extract_pt_nodes()
        logger.info(f"Found {len(pt_nodes)} PT stops with coordinates")
        
        if len(pt_nodes) == 0:
            logger.error("❌ No PT nodes found! Check your graph structure.")
            return {"error": "no_pt_nodes"}
        
        # Build spatial index
        node_ids, coords = self.build_spatial_index(pt_nodes)
        logger.info("Built spatial index (KDTree)")
        
        # Find and add walking connections
        stats = self.add_connections(node_ids, coords)
        
        logger.info(f"\n✅ Walking connection generation complete!")
        logger.info(f"   Added {stats['edges_added']:,} walking edges")
        logger.info(f"   Between {stats['unique_pairs']:,} unique stop pairs")
        
        # Analyze by mode
        self._analyze_by_mode()
        
        return stats
    
    def extract_pt_nodes(self):
        pt_nodes = []

        for node_id, node_data in self.graph.nodes(data=True):
            if 'lat' in node_data and 'lon' in node_data:
                pt_nodes.append((node_id, node_data))
            else:
                logger.warning(f"Node {node_id} missing coordinates, skipping")
            
        return pt_nodes
    
    def build_spatial_index(self, pt_nodes):
        """ Build KDTree for efficient nearest-neighbor search """
        node_ids = []
        coords = []
        
        for node_id, node_data in pt_nodes:
            lat = node_data['lat']
            lon = node_data['lon']
            node_ids.append(node_id)
            coords.append([lat, lon])
        
        coords = np.array(coords)
        tree = KDTree(coords)
        
        self.pt_node_ids = node_ids
        self.pt_coords = coords
        self.pt_tree = tree
        
        return node_ids, coords
    
    def add_connections(self, node_ids, coords):
        #Build KDTree
        tree = KDTree(coords)

        stats = {
            'edges_added': 0,
            'unique_pairs': 0,
            'nodes_checked': 0,
            'skipped_existing': 0,
            'skipped_too_far': 0
        }

        pairs_added = set()
        
        # Convert max distance to approximate degrees
        lat_avg = np.mean(coords[:, 0])
        meters_per_degree_lat = 111320
        meters_per_degree_lon = 111320 * np.cos(np.radians(lat_avg))
        search_radius_degrees = self.max_walk_distance / min(meters_per_degree_lat, meters_per_degree_lon)
        

        #For each node, find nearby node
        for i, node_id in enumerate(node_ids):
            stats['nodes_checked'] += 1

            #Find all nodes within search radius
            indices = tree.query_ball_point(coords[i], search_radius_degrees)
            
            for j in indices:
                if i == j:  # Skip self and already processed pairs
                    continue
                
                neighbor_id = node_ids[j]
                
                # Calculate exact distance
                distance = self._calculate_distance(coords[i], coords[j])
                
                # Check if within walking distance
                if distance > self.max_walk_distance:
                    stats['skipped_too_far'] += 1
                    continue
                
                # Check if edge already exists
                if self.graph.has_edge(node_id, neighbor_id):
                    stats['skipped_existing'] += 1
                    continue
                
                # Add bidirectional walking edges
                self._add_walking_edge(node_id, neighbor_id, distance)
                self._add_walking_edge(neighbor_id, node_id, distance)
                
                stats['edges_added'] += 2
                pairs_added.add(tuple(sorted([node_id, neighbor_id])))
                
                # Log progress
                if len(pairs_added) % 50 == 0:
                    logger.info(f"   Progress: {len(pairs_added)} stop pairs connected...")
        
        stats['unique_pairs'] = len(pairs_added)
        return stats
    
    def _calculate_distance(self, coord1, coord2):
        """Calculate geodesic distance between two coordinates"""
        return geodesic((coord1[0], coord1[1]), (coord2[0], coord2[1])).meters
    
    def _add_walking_edge(self, source, target, distance):
        """Add a single walking edge with calculated attributes"""
        
        # Calculate travel time
        travel_time = distance / self.walking_speed  # seconds
        
        # Walking has zero emissions
        emissions = 0.0
        
        # Add edge
        self.graph.add_edge(
            source,
            target,
            mode='walk',
            distance=distance,
            time=travel_time,
            emissions=emissions,
            edge_type='pt_transfer',
            walk_distance_m=round(distance, 1),
            walk_time_min=round(travel_time / 60, 1)
        )
    
    def _analyze_by_mode(self):
        """Analyze walking connections by transport mode"""
        
        logger.info("\n📊 Analyzing transfers by mode...")
        
        # Categorize nodes by mode
        node_modes = {}
        for node in self.graph.nodes():
            modes = set()
            for neighbor in self.graph[node]:
                edge = self.graph[node][neighbor]
                mode = edge.get('mode')
                route_type = edge.get('route_type')
                
                if mode and mode != 'walk':
                    modes.add(mode)
                elif route_type in [1, 2]:
                    modes.add('train')
                elif route_type == 0:
                    modes.add('tram')
                elif route_type == 3:
                    modes.add('bus')
            
            node_modes[node] = modes
        
        # Count transfer types
        transfer_counts = {
            'train↔train': 0,
            'train↔tram': 0,
            'train↔bus': 0,
            'tram↔tram': 0,
            'tram↔bus': 0,
            'bus↔bus': 0,
            'other': 0
        }
        
        for u, v, data in self.graph.edges(data=True):
            if data.get('mode') != 'walk' or data.get('edge_type') != 'pt_transfer':
                continue
            
            u_modes = node_modes.get(u, set())
            v_modes = node_modes.get(v, set())
            
            if 'train' in u_modes and 'train' in v_modes:
                transfer_counts['train↔train'] += 1
            elif ('train' in u_modes and 'tram' in v_modes) or ('tram' in u_modes and 'train' in v_modes):
                transfer_counts['train↔tram'] += 1
            elif ('train' in u_modes and 'bus' in v_modes) or ('bus' in u_modes and 'train' in v_modes):
                transfer_counts['train↔bus'] += 1
            elif 'tram' in u_modes and 'tram' in v_modes:
                transfer_counts['tram↔tram'] += 1
            elif ('tram' in u_modes and 'bus' in v_modes) or ('bus' in u_modes and 'tram' in v_modes):
                transfer_counts['tram↔bus'] += 1
            elif 'bus' in u_modes and 'bus' in v_modes:
                transfer_counts['bus↔bus'] += 1
            else:
                transfer_counts['other'] += 1
        
        logger.info("\n   Transfer types:")
        for transfer_type, count in sorted(transfer_counts.items()):
            if count > 0:
                logger.info(f"      {transfer_type:15s}: {count:,}")


def main():
    """Main execution"""
    
    logger.info("="*60)
    logger.info("PT WALKING CONNECTION GENERATOR")
    logger.info("="*60)
    
    # Load PT graph
    logger.info(f"\nLoading PT graph from {PT_GRAPH_PATH}...")
    try:
        with open(PT_GRAPH_PATH, 'rb') as f:
            G = pickle.load(f)
        logger.info(f"✅ Loaded: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    except FileNotFoundError:
        logger.error(f"❌ PT graph not found at {PT_GRAPH_PATH}")
        logger.error("Please update PT_GRAPH_RAW_PATH in config_integration.py")
        return
    
    # Check before stats
    logger.info("\n📊 BEFORE adding walking connections:")
    logger.info(f"   Nodes: {G.number_of_nodes():,}")
    logger.info(f"   Edges: {G.number_of_edges():,}")
    
    # Add walking connections
    builder = PTWalkingConnectionBuilder(G, max_walk_distance=MAX_WALKING_DISTANCE_M)
    stats = builder.add_walking_edges()
    
    if "error" in stats:
        logger.error("Failed to add walking connections")
        return
    
    # Check after stats
    logger.info("\n📊 AFTER adding walking connections:")
    logger.info(f"   Nodes: {G.number_of_nodes():,}")
    logger.info(f"   Edges: {G.number_of_edges():,}")
    
    # Check connectivity
    if isinstance(G, nx.DiGraph):
        weak_components = nx.number_weakly_connected_components(G)
        logger.info(f"   Weakly connected components: {weak_components}")
    
    # Save updated graph
    logger.info(f"\n💾 Saving PT graph with walking connections...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(PT_GRAPH_PATH, 'wb') as f:
        pickle.dump(G, f)
    
    logger.info(f"✅ Saved to {PT_GRAPH_PATH}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ PT WALKING CONNECTIONS COMPLETE")
    logger.info("="*60)
    logger.info(f"\nAdded {stats['edges_added']:,} walking edges")
    logger.info(f"Output: {PT_GRAPH_PATH}")
    logger.info("\nNext step:")
    logger.info("  Run: python 2_identify_train_stations.py")


if __name__ == "__main__":
    main()