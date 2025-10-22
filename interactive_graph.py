"""
Step 5: Visualize Combined Multimodal Graph
Creates interactive HTML map with Folium
"""
import folium
import networkx as nx
import pickle
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_integration import (
    COMBINED_GRAPH_PATH, COMBINED_VISUALIZATION,
    MODE_COLORS, LOG_LEVEL, LOG_FORMAT
)

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def load_combined_graph():
    """Load the combined graph"""
    logger.info(f"Loading combined graph from {COMBINED_GRAPH_PATH}...")
    
    with open(COMBINED_GRAPH_PATH, 'rb') as f:
        G = pickle.load(f)
    
    logger.info(f"✅ Loaded: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G


def create_map(G):
    """Create interactive Folium map"""
    
    logger.info("\nCreating interactive map...")
    
    # Calculate center point
    lats = [d['lat'] for n, d in G.nodes(data=True) if 'lat' in d]
    lons = [d['lon'] for n, d in G.nodes(data=True) if 'lon' in d]
    
    avg_lat = sum(lats) / len(lats)
    avg_lon = sum(lons) / len(lons)
    
    logger.info(f"Map center: ({avg_lat:.6f}, {avg_lon:.6f})")
    
    # Create map
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    return m


def add_edges_to_map(m, G):
    """Add all edges to the map by mode"""
    
    logger.info("\nAdding edges to map...")
    
    # Count edges by mode
    mode_counts = {}
    
    # Group edges by mode for efficient drawing
    edges_by_mode = {}
    
    for u, v, data in G.edges(data=True):
        from_node = G.nodes[u]
        to_node = G.nodes[v]
        
        # Skip if either node missing coordinates
        if 'lat' not in from_node or 'lat' not in to_node:
            continue
        
        mode = data.get('mode', 'unknown')
        edge_type = data.get('edge_type', '')
        
        # Special handling for car-to-PT connections
        if edge_type == 'car_to_pt_transfer':
            display_mode = 'connection'
        else:
            display_mode = mode
        
        if display_mode not in edges_by_mode:
            edges_by_mode[display_mode] = []
        
        edges_by_mode[display_mode].append((u, v, data))
        mode_counts[display_mode] = mode_counts.get(display_mode, 0) + 1
    
    # Draw edges by mode (in specific order for layering)
    draw_order = ['car', 'walk', 'bus', 'tram', 'train', 'connection']
    
    for mode in draw_order:
        if mode not in edges_by_mode:
            continue
        
        edges = edges_by_mode[mode]
        color = MODE_COLORS.get(mode, '#95a5a6')
        
        logger.info(f"  Drawing {len(edges):,} {mode} edges...")
        
        # Determine line properties
        if mode == 'car':
            weight = 1.5
            opacity = 0.7
        elif mode == 'train':
            weight = 4.0
            opacity = 0.9
        elif mode == 'tram':
            weight = 3.0
            opacity = 0.8
        elif mode == 'bus':
            weight = 2.0
            opacity = 0.7
        elif mode == 'connection':
            weight = 3.0
            opacity = 0.9
        else:  # walk
            weight = 1.0
            opacity = 0.4
        
        # Draw edges (sample if too many)
        sample_size = 2000 if mode == 'car' else len(edges)
        
        for u, v, data in edges[:sample_size]:
            from_node = G.nodes[u]
            to_node = G.nodes[v]
            
            # Create popup
            distance = data.get('distance', 0)
            time = data.get('time', 0)
            
            popup_html = f"""
            <b>Mode:</b> {mode}<br>
            <b>Distance:</b> {distance:.1f}m<br>
            <b>Time:</b> {time/60:.1f} min
            """
            
            if mode == 'connection':
                station_name = data.get('station_name', 'Unknown')
                popup_html = f"""
                <b>🚗→🚉 Car to Train Transfer</b><br>
                <b>Station:</b> {station_name}<br>
                <b>Walking:</b> {distance:.1f}m ({time/60:.1f} min)
                """
            
            folium.PolyLine(
                [(from_node['lat'], from_node['lon']),
                 (to_node['lat'], to_node['lon'])],
                color=color,
                weight=weight,
                opacity=opacity,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)
        
        if len(edges) > sample_size:
            logger.info(f"    (sampled {sample_size:,} of {len(edges):,} for performance)")
    
    return mode_counts


def add_train_station_markers(m, G):
    """Add markers for train stations"""
    
    logger.info("\nAdding train station markers...")
    
    train_stations = []
    
    # Find train station nodes
    for node, data in G.nodes(data=True):
        if 'lat' not in data or 'lon' not in data:
            continue
        
        # Check if this node connects to train edges
        is_train_station = False
        for neighbor in G[node]:
            edge = G[node][neighbor]
            if edge.get('mode') == 'train' or edge.get('route_type') in [1, 2]:
                is_train_station = True
                break
        
        if is_train_station:
            station_name = data.get('station_name', str(node))
            train_stations.append((node, station_name, data['lat'], data['lon']))
    
    logger.info(f"  Adding {len(train_stations)} train station markers...")
    
    for node_id, name, lat, lon in train_stations:
        folium.Marker(
            location=[lat, lon],
            popup=f"<b>🚉 {name}</b><br>ID: {node_id}",
            icon=folium.Icon(color='blue', icon='train', prefix='fa'),
            tooltip=name
        ).add_to(m)


def add_legend(m, mode_counts):
    """Add legend to map"""
    
    logger.info("\nAdding legend...")
    
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 250px; height: auto; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 15px; border-radius: 5px; 
                box-shadow: 0 0 15px rgba(0,0,0,0.2);">
    <p style="margin-bottom: 10px; font-weight: bold; font-size: 16px;">
        🗺️ Transport Modes
    </p>
    '''
    
    mode_labels = {
        'car': '🚗 Car Roads',
        'train': '🚆 Train',
        'tram': '🚊 Tram',
        'bus': '🚌 Bus',
        'walk': '🚶 Walking',
        'connection': '🔗 Car→Train'
    }
    
    for mode, label in mode_labels.items():
        count = mode_counts.get(mode, 0)
        if count > 0:
            color = MODE_COLORS.get(mode, '#95a5a6')
            legend_html += f'''
            <p style="margin: 5px 0;">
                <span style="background-color:{color}; width: 30px; height: 3px; 
                             display: inline-block; vertical-align: middle;"></span>
                {label} ({count:,})
            </p>
            '''
    
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))


def add_title(m, G):
    """Add title overlay"""
    
    title_html = f'''
    <div style="position: fixed; 
                top: 10px; left: 50px; width: 450px; height: auto; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:16px; padding: 15px; border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2);">
    <p style="margin: 0; font-weight: bold; font-size: 20px;">
        🌐 Multimodal Transport Network
    </p>
    <p style="margin: 5px 0; font-size: 14px; color: #666;">
        Burnley → Hawthorn → Camberwell Corridor
    </p>
    <p style="margin: 5px 0; font-size: 12px; color: #999;">
        {G.number_of_nodes():,} nodes | {G.number_of_edges():,} edges
    </p>
    <p style="margin: 5px 0; font-size: 11px; color: #999; font-style: italic;">
        Click edges for details | Blue markers = Train stations
    </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))


def save_map(m):
    """Save the map to HTML file"""
    
    logger.info(f"\n💾 Saving map to {COMBINED_VISUALIZATION}...")
    
    os.makedirs(os.path.dirname(COMBINED_VISUALIZATION), exist_ok=True)
    m.save(COMBINED_VISUALIZATION)
    
    logger.info("✅ Saved")


def main():
    """Main execution"""
    
    logger.info("="*60)
    logger.info("COMBINED GRAPH VISUALIZATION")
    logger.info("="*60)
    
    # Load graph
    G = load_combined_graph()
    
    # Create map
    m = create_map(G)
    
    # Add edges
    mode_counts = add_edges_to_map(m, G)
    
    # Add train station markers
    add_train_station_markers(m, G)
    
    # Add legend and title
    add_legend(m, mode_counts)
    add_title(m, G)
    
    # Save
    save_map(m)
    
    logger.info("\n" + "="*60)
    logger.info("✅ VISUALIZATION COMPLETE")
    logger.info("="*60)
    logger.info(f"\n📂 Open this file in your browser:")
    logger.info(f"   {COMBINED_VISUALIZATION}")
    logger.info("\nFeatures:")
    logger.info("  🗺️  Interactive map with zoom/pan")
    logger.info("  🎨 Color-coded by transport mode")
    logger.info("  📍 Blue markers = Train stations")
    logger.info("  💬 Click any edge for details")
    logger.info("  🔗 Purple lines = Car→Train connections")


if __name__ == "__main__":
    main()