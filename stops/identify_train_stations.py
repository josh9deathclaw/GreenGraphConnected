""" 
Identify train stations from PT Graph
Extract all nodes that correspond to train stations (route type 1 or 2)
"""

import networkx as nx
import pickle
import json
import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_integration import (
    PT_GRAPH_PATH, TRAIN_STATIONS_JSON, OUTPUT_DIR,
    TRAIN_ROUTE_TYPES, MIN_TRAIN_STATIONS_EXPECTED, 
    MAX_TRAIN_STATIONS_EXPECTED, LOG_LEVEL, LOG_FORMAT
)

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def load_pt_graph():
    logger.info(f"Loading PT graph from {PT_GRAPH_PATH}...")
    
    try:
        with open(PT_GRAPH_PATH, 'rb') as f:
            G = pickle.load(f)
        logger.info(f"✅ Loaded: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
        return G
    except FileNotFoundError:
        logger.error(f"❌ PT graph not found at {PT_GRAPH_PATH}")
        logger.error("Please update PT_GRAPH_PATH in config_integration.py")
        raise
    except Exception as e:
        logger.error(f"❌ Error loading PT graph: {e}")
        raise

def identify_train_stations(G):
    """
        Steps:
            Iterate through all edges in the graph
            Find edges where route type is 1 or 2 (train)
            Extract nodes (stations) those edges connect to
            Remove duplicates
    """

    logger.info("\nIdentifying train stations...")
    
    train_station_nodes = set()
    train_edges_found = 0

    # Method 1: Check edges for train route_type
    for u, v, data in G.edges(data=True):
        route_type = data.get('route_type')
        mode = data.get('mode')
        
        # Check if this is a train edge
        if route_type in TRAIN_ROUTE_TYPES or mode == 'train':
            train_station_nodes.add(u)
            train_station_nodes.add(v)
            train_edges_found += 1
    
    logger.info(f"Found {train_edges_found:,} train edges")
    logger.info(f"Found {len(train_station_nodes):,} unique train station nodes")
    
    # Validate results
    if len(train_station_nodes) < MIN_TRAIN_STATIONS_EXPECTED:
        logger.warning(f"⚠️  Only found {len(train_station_nodes)} stations, expected at least {MIN_TRAIN_STATIONS_EXPECTED}")
        logger.warning("This might indicate an issue with the PT graph or route_type tagging")
    
    if len(train_station_nodes) > MAX_TRAIN_STATIONS_EXPECTED:
        logger.warning(f"⚠️  Found {len(train_station_nodes)} stations, expected max {MAX_TRAIN_STATIONS_EXPECTED}")
        logger.warning("This might indicate stops are not properly grouped into stations")
    
    return train_station_nodes

def extract_station_data(G, train_station_nodes):
    logger.info("\nExtracting station details...")
    
    stations = []
    missing_coords = 0
    missing_names = 0
    
    for node_id in train_station_nodes:
        node_data = G.nodes[node_id]
        
        # Get coordinates
        lat = node_data.get('lat')
        lon = node_data.get('lon')
        
        if lat is None or lon is None:
            missing_coords += 1
            logger.warning(f"⚠️  Node {node_id} missing coordinates")
            continue
        
        # Get station name
        station_name = node_data.get('station_name') or node_data.get('stop_name') or str(node_id)
        
        if station_name == str(node_id):
            missing_names += 1
        
        stations.append({
            'id': node_id,
            'name': station_name,
            'lat': lat,
            'lon': lon,
            'node_type': 'train_station'
        })
    
    logger.info(f"✅ Extracted {len(stations)} stations with complete data")
    
    if missing_coords > 0:
        logger.warning(f"⚠️  {missing_coords} stations missing coordinates (excluded)")
    
    if missing_names > 0:
        logger.warning(f"⚠️  {missing_names} stations missing names (using node ID)")
    
    # Sort by name for easier reading
    stations.sort(key=lambda x: x['name'])
    
    return stations

def save_stations(stations):
    """Save station data to JSON file"""
    logger.info(f"\n💾 Saving station data to {TRAIN_STATIONS_JSON}...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(TRAIN_STATIONS_JSON, 'w') as f:
        json.dump(stations, f, indent=2)
    
    logger.info("✅ Saved")

def print_station_summary(stations):
    """Print summary of identified stations"""
    logger.info("\n" + "="*60)
    logger.info("TRAIN STATION SUMMARY")
    logger.info("="*60)
    
    logger.info(f"\nTotal stations: {len(stations)}")
    
    # Calculate bounding box
    if stations:
        lats = [s['lat'] for s in stations]
        lons = [s['lon'] for s in stations]
        
        logger.info(f"\nGeographic extent:")
        logger.info(f"  Latitude:  {min(lats):.6f} to {max(lats):.6f}")
        logger.info(f"  Longitude: {min(lons):.6f} to {max(lons):.6f}")
    
    # Show first 10 stations
    logger.info(f"\nFirst 10 stations:")
    for i, station in enumerate(stations[:10], 1):
        logger.info(f"  {i:2d}. {station['name']}")
        logger.info(f"      ID: {station['id']}")
        logger.info(f"      Location: ({station['lat']:.6f}, {station['lon']:.6f})")
    
    if len(stations) > 10:
        logger.info(f"  ... and {len(stations) - 10} more stations")


def main():
    """Main execution"""
    
    logger.info("="*60)
    logger.info("TRAIN STATION IDENTIFICATION")
    logger.info("="*60)
    
    # Load PT graph
    G = load_pt_graph()
    
    # Identify train stations
    train_station_nodes = identify_train_stations(G)
    
    if not train_station_nodes:
        logger.error("❌ No train stations found!")
        logger.error("\nPossible issues:")
        logger.error("  1. PT graph doesn't have 'route_type' attribute on edges")
        logger.error("  2. No train routes in the POC area")
        logger.error("  3. Wrong PT graph loaded")
        return
    
    # Extract station data
    stations = extract_station_data(G, train_station_nodes)
    
    if not stations:
        logger.error("❌ No stations with valid coordinates!")
        return
    
    # Save to JSON
    save_stations(stations)
    
    # Print summary
    print_station_summary(stations)
    
    logger.info("\n" + "="*60)
    logger.info("✅ TRAIN STATION IDENTIFICATION COMPLETE")
    logger.info("="*60)
    logger.info(f"\nOutput: {TRAIN_STATIONS_JSON}")
    logger.info("\nNext step:")
    logger.info("  Run: python 2_connect_car_to_pt.py")


if __name__ == "__main__":
    main()