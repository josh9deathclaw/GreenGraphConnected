"""
Configuration for Graph Integration
Connects Car Graph with PT Graph
"""

# PT Graph (from your PT graph folder - WITHOUT walking connections yet)
PT_GRAPH_PATH = 'data/graphs/pt_graph.gpickle'

# Car Graph (from your car graph folder)
CAR_GRAPH_PATH = 'data/graphs/car_graph.gpickle'

# Output path for the integrated graph
OUTPUT_DIR = 'data/graphs'
TRAIN_STATIONS_JSON = f'{OUTPUT_DIR}/train_stations.json'
CONNECTION_REPORT = f'{OUTPUT_DIR}/connection_report.txt'
COMBINED_GRAPH_PATH = f'{OUTPUT_DIR}/combined_graph.gpickle'
COMBINED_VISUALIZATION = f'{OUTPUT_DIR}/combined_network.html'
STATIC_GRAPH_IMAGE = f'{OUTPUT_DIR}/combined_network.png'

# Train Station Identification (GTFS route_type for trains)
TRAIN_ROUTE_TYPES = [1, 2]

# Connection Parameters
MAX_WALKING_DISTANCE_M = 300 #meters
WALKING_SPEED = 1.4 #meters per second

# Graph Validation
MIN_TRAIN_STATIONS_EXPECTED = 5   # Sanity check: expect at least 5 train stations
MAX_TRAIN_STATIONS_EXPECTED = 50  # Sanity check: shouldn't have more

#Visualization Parameters
MODE_COLORS = {
    'car': '#e74c3c',        # Red
    'train': '#3498db',      # Blue
    'tram': '#2ecc71',       # Green
    'bus': '#f39c12',        # Orange
    'walk': '#95a5a6',       # Gray
    'connection': '#9b59b6'  # Purple (car-to-PT transfers)
}

# Edge weights for visualization
MODE_WEIGHTS = {
    'car': 1.5,
    'train': 3.0,
    'tram': 2.5,
    'bus': 2.0,
    'walk': 1.0,
    'connection': 2.0
}

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Debugging
# Set to True to enable verbose debugging output
DEBUG_MODE = False

# Set to True to save intermediate graphs at each step
SAVE_INTERMEDIATE_GRAPHS = True

# Set to True to generate detailed connection logs
DETAILED_CONNECTION_LOGS = True