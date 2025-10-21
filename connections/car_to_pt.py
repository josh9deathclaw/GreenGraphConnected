"""
Connect Car Network to PT Network
One-Way Walking Edges from Road Nodes to Train Stations
"""

import networkx as nx
import pickle
import json
import logging
import os
from geopy.distance import geodesic
from scipy.spatial import KDTree
import numpy as np
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_integration import (
    CAR_GRAPH_PATH, TRAIN_STATIONS_JSON, CONNECTION_REPORT,
    OUTPUT_DIR, MAX_WALKING_DISTANCE_M, WALKING_SPEED,
    LOG_LEVEL, LOG_FORMAT, DETAILED_CONNECTION_LOGS
)

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

class CarToPTConnector:
    def __init__(self, max_distance=MAX_WALKING_DISTANCE_M):
        self.max_distance = max_distance
        self.walking_speed = WALKING_SPEED
        self.connections = []

    def load_graphs(self):
        """Load car graph and train stations"""
        logger.info(f"Loading car graph from {CAR_GRAPH_PATH}...")
        
        try:
            with open(CAR_GRAPH_PATH, 'rb') as f:
                self.G_car = pickle.load(f)
            logger.info(f"✅ Car graph loaded: {self.G_car.number_of_nodes():,} nodes, {self.G_car.number_of_edges():,} edges")
        except FileNotFoundError:
            logger.error(f"❌ Car graph not found at {CAR_GRAPH_PATH}")
            raise
        
        logger.info(f"\nLoading train stations from {TRAIN_STATIONS_JSON}...")
        
        try:
            with open(TRAIN_STATIONS_JSON, 'r') as f:
                self.train_stations = json.load(f)
            logger.info(f"✅ Loaded {len(self.train_stations)} train stations")
        except FileNotFoundError:
            logger.error(f"❌ Train stations file not found at {TRAIN_STATIONS_JSON}")
            logger.error("Run 1_identify_train_stations.py first")
            raise

    def build_spatial_index(self):
        """Build KDTree for efficient nearest-neighbor search"""
        logger.info("\nBuilding spatial index for road nodes...")
        
        # Extract road node coordinates
        self.road_nodes = []
        self.road_coords = []
        
        for node_id, node_data in self.G_car.nodes(data=True):
            lat = node_data.get('lat')
            lon = node_data.get('lon')
            
            if lat and lon:
                self.road_nodes.append(node_id)
                self.road_coords.append([lat, lon])
        
        self.road_coords = np.array(self.road_coords)
        self.road_tree = KDTree(self.road_coords)
        
        logger.info(f"✅ Indexed {len(self.road_nodes):,} road nodes")
        
    def find_connections(self):
        """Find nearest road node for each train station"""
        logger.info("\n" + "="*60)
        logger.info("FINDING CONNECTIONS")
        logger.info("="*60)
        logger.info(f"Max walking distance: {self.max_distance}m")
        
        self.connections = []
        stations_connected = 0
        stations_too_far = 0
        
        for station in self.train_stations:
            station_coord = [station['lat'], station['lon']]
            
            # Convert max distance to approximate degrees for KDTree
            search_radius_deg = self.max_distance / 111320
            
            # Find all road nodes within search radius
            indices = self.road_tree.query_ball_point(station_coord, search_radius_deg)
            
            if not indices:
                stations_too_far += 1
                logger.warning(f"⚠️  {station['name']}: No road nodes within {self.max_distance}m")
                continue
            
            # Calculate exact distances and find closest
            closest_road = None
            min_distance = float('inf')  # ← FIXED: Initialize here!
            
            for idx in indices:
                road_node_id = self.road_nodes[idx]
                road_coord = self.road_coords[idx]
                
                # Calculate exact distance
                distance = geodesic(station_coord, road_coord).meters
                
                if distance < min_distance and distance <= self.max_distance:
                    min_distance = distance
                    closest_road = road_node_id
            
            if closest_road:
                # Calculate walking time
                walk_time = min_distance / self.walking_speed
                
                connection = {
                    'station_id': station['id'],
                    'station_name': station['name'],
                    'station_lat': station['lat'],
                    'station_lon': station['lon'],
                    'road_node': closest_road,
                    'road_lat': self.G_car.nodes[closest_road]['lat'],
                    'road_lon': self.G_car.nodes[closest_road]['lon'],
                    'distance': min_distance,
                    'walk_time': walk_time
                }
                
                self.connections.append(connection)
                stations_connected += 1
                
                logger.info(f"✅ {station['name']}: {closest_road} ({min_distance:.1f}m, {walk_time/60:.1f}min)")
            else:
                stations_too_far += 1
                logger.warning(f"⚠️  {station['name']}: No road within {self.max_distance}m")
        
        logger.info(f"\n📊 Connection Summary:")
        logger.info(f"  Stations connected: {stations_connected} / {len(self.train_stations)}")
        logger.info(f"  Stations too far: {stations_too_far}")
        
        if stations_connected == 0:
            logger.error("❌ No connections found! Check that both graphs cover the same area.")
            raise ValueError("No connections found")
    
        return self.connections

    def generate_report(self):
        logger.info(f"\nGenerating connection report at {CONNECTION_REPORT}...")

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        with open(CONNECTION_REPORT, 'w') as f:
            f.write("="*60 + "\n")
            f.write("CAR TO PT CONNECTION REPORT\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Total train stations: {len(self.train_stations)}\n")
            f.write(f"Stations connected: {len(self.connections)}\n")
            f.write(f"Stations not connected: {len(self.train_stations) - len(self.connections)}\n")
            f.write(f"Max walking distance: {self.max_distance}m\n\n")
            
            f.write("="*60 + "\n")
            f.write("CONNECTION DETAILS\n")
            f.write("="*60 + "\n\n")
            
            for i, conn in enumerate(self.connections, 1):
                f.write(f"{i}. {conn['station_name']}\n")
                f.write(f"   Station ID: {conn['station_id']}\n")
                f.write(f"   Station Location: ({conn['station_lat']:.6f}, {conn['station_lon']:.6f})\n")
                f.write(f"   Connected to Road Node: {conn['road_node']}\n")
                f.write(f"   Road Location: ({conn['road_lat']:.6f}, {conn['road_lon']:.6f})\n")
                f.write(f"   Walking Distance: {conn['distance']:.1f}m\n")
                f.write(f"   Walking Time: {conn['walk_time']/60:.1f} minutes\n\n")
            
            # Statistics
            if self.connections:
                distances = [c['distance'] for c in self.connections]
                times = [c['walk_time']/60 for c in self.connections]
                
                f.write("="*60 + "\n")
                f.write("STATISTICS\n")
                f.write("="*60 + "\n\n")
                f.write(f"Average walking distance: {np.mean(distances):.1f}m\n")
                f.write(f"Min walking distance: {np.min(distances):.1f}m\n")
                f.write(f"Max walking distance: {np.max(distances):.1f}m\n")
                f.write(f"Average walking time: {np.mean(times):.1f} minutes\n")
        
        logger.info(f"✅ Report saved to {CONNECTION_REPORT}")


def main():
    """Main execution"""
    
    logger.info("="*60)
    logger.info("CAR TO PT CONNECTION")
    logger.info("="*60)
    
    # Create connector
    connector = CarToPTConnector()
    
    # Load data
    connector.load_graphs()
    
    # Build spatial index
    connector.build_spatial_index()
    
    # Find connections
    connections = connector.find_connections()
    
    # Generate report
    connector.generate_report()
    
    # Save connections as JSON for next step
    connections_file = os.path.join(OUTPUT_DIR, 'connections.json')
    with open(connections_file, 'w') as f:
        json.dump(connections, f, indent=2)
    logger.info(f"💾 Connections saved to {connections_file}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ CONNECTION FINDING COMPLETE")
    logger.info("="*60)
    logger.info(f"\nFound {len(connections)} connections")
    logger.info(f"Report: {CONNECTION_REPORT}")
    logger.info("\nNext step:")
    logger.info("  Run: python 4_merge_graphs.py")


if __name__ == "__main__":
    main()