"""
File: maze.py
Description: Defines the Maze class, which represents the map of the simulated world. 

# Intro to Maze Class
The Maze class models the 2D map in which agents move.
There are two representations of the map: 1) tiled map; 2) graph.
Here the backend only handles abstract network.
Frontend will deal with the tile world for visualization.
  
# How agents move on the map
• A real-time shortest path can be found by get_shortest_path.
• The travel mode can be either driving or walk + transit.
"""
import json
import networkx as nx
import matplotlib.pyplot as plt
from gatsim import config 
from gatsim.utils import pretty_print
import csv
import os
from operator import itemgetter
from datetime import datetime, timedelta

"""
Network event class; used for events that affect transportation network attributes, like capacity.
Events are stored at gatsim/map/events.json.
events.json contains a list of events, each event is a dictionary.
An event is a dictionary, example:
    {
      "place": "Ave_2_link_2",
      "direction": 0,
      "attribute": "realtime capacity",
      "old_value": 2,
      "new_value": 1,
      "start_time": "2025-03-10 08:10:00",
      "preview_time": "2025-03-10 08:10:00",
      "duration": 40,
      "content": "Ave_2_link_2 direction 0 realtime capacity drop from 2 to 1 due to car accident from 2025-03-10 08:00; duration is 40 minutes",
      "keywords": ["Ave_2_link_2", "car accident", "morning"],
      "spatial_scope": "Ave_1_link_2",
      "time_scope": ["08:10:00", "08:50:00"],    
      "broadcast": false
    }
"""

class NetworkEvent:
    """ 
    Class used to store network events.
    """
    def __init__(self,
                 place,
                 direction,
                 attribute,
                 old_value,
                 new_value,
                 start_time,
                 preview_time,
                 duration,
                 content,
                 keywords,
                 spatial_scope,
                 time_scope,
                 broadcast,  # whether this event should be broadcast to the whole maze
                 ):
        """
        Instance variables:      
        - place (str):  link / node / facility name; must be a valid node/link/facility name.
        - direction (int): link direction; applicable only if place is a link;
        - attribute (str): affected attribute, say "realtime capacity", "wait time", "travel time"
        - old_value (int):  # old value of the attribute
        - new_value (int):  # new value of the attribute
        - start_time (datetime):  # start time of the event; datetime object;
        - preview_time (datetime):  # preview time of the event; datetime object;
        - duration (datetime.timedelta):  # duration of the event (in minutes); timedelta object;
        - content (str): Memory content, e.g. "St_3_link_2 was severely congested around 8 AM on Monday."
        - keywords (list[str]): keywords for retrieval, e.g. ["St_3_link_2", "congestion", "morning"]
        - spatial_level (str): spatial_scope spatial_level; "node" | "link" | 'road' | "path" | "zone" | "network" | None
                None if the concept does not contain spatial information;
        - spatial_scope (str): "Node_1" | "St_3_link_2" | "Ave_1" | "Uptown apartment to Office" | "School zone" | "the town" | None
                None if the concept does not contain spatial information;
        - time_scope (list[datetime.time]): time scope of the concept; a list of two elements; e.g. [time(8, 0), time(9,0)]
        - broadcast:  # whether this event should be broadcast to the whole network
        """
        self.place = place
        self.direction = direction
        self.attribute = attribute
        self.old_value = old_value
        self.new_value = new_value
        self.start_time = start_time
        self.preview_time = preview_time
        self.duration = duration
        self.content = content
        self.keywords = keywords
        self.spatial_scope = spatial_scope
        self.time_scope = time_scope
        self.broadcast = broadcast
        

class Maze: 
    def __init__(self, maze_name): 
        #======================Load transportation network data====================
        # abstract transportation network is a graph G=(V, E)
        # we need to transform tile map to classical transportation network
        # we only consider bidirectional network.
        # V: nodes; facilities are attached with nodes;
        # E: links; links are the roads or transit segments connecting the nodes;
        if not maze_name:
            maze_name = config.maze_name
        self.maze_name = maze_name
        self.broadcast_news = []  # the list of broadcast news
        # load vertices and facilities info
        self.nodes_info = json.load(open(f"{config.maze_assets_loc}/nodes_info.json"))
        self.num_nodes = len(self.nodes_info)
        # Load the facilities info
        self.facilities_info = json.load(open(f"{config.maze_assets_loc}/facilities_info.json"))
        self.num_facilities = len(self.facilities_info)
        # facility2node
        self.facility2node = {}
        for node, attr in self.nodes_info.items():
            for facility in attr['facilities']:
                self.facility2node[facility] = node
                
        # load links
        self.links_info = json.load(open(f"{config.maze_assets_loc}/links_info.json"))
        self.num_links = len(self.links_info)
        # Note: all links are bi-directional!
        # direction 0 is from self.links_info[link]['endpoints'][0] to self.links_info[link]['endpoints'][1]
        # direction 1 is from self.links_info[link]['endpoints'][1] to self.links_info[link]['endpoints'][0]
            
        # add events property to nodes, links, and facilities
        for node in self.nodes_info:
            self.nodes_info[node]['events'] = []
            self.nodes_info[node]['waiting'] = []  # add waiting personas list; a list of persona names
            
        for link, attr in self.links_info.items():
            # initialize realtime capacity to base capacity
            # if accidents happen, realtime capacity may be adjusted smaller
            self.links_info[link]['realtime_capacity'] = (attr['base_capacity'], attr['base_capacity'])  # bi-directional
            self.links_info[link]['events'] = [[], []]  # bi-directional
            wait_time = int(self.links_info[link]['wait_time'])
            self.links_info[link]['wait_time'] = [wait_time, wait_time]  # wait time of link for each direction
            if self.links_info[link]['type'] == 'road':
                self.links_info[link]['driving'] = [[], []]  # bi-directional
                # personas currently driving on the link; a list of persona names
                self.links_info[link]['walking'] = [[], []]  # bi-directional
                # personas currently walking on the link; a list of persona names
                self.links_info[link]['waiting'] = [[], []]  # bi-directional
                # personas currently waiting on the link; a list of persona names
            elif self.links_info[link]['type'] == 'metro':
                self.links_info[link]['riding'] = [[], []]  # bi-directional
                # personas currently ridding on the link; a list of persona names
                self.links_info[link]['waiting'] = [[], []]  # bi-directional
                # personas currently waiting on the link; a list of persona names
                self.links_info[link]['arrival'] = [False, False]  # whether the train currently arrived at the station for each direction
                
        for facility, attr in self.facilities_info.items():
            self.facilities_info[facility]['realtime_capacity'] = attr['base_capacity']
            self.facilities_info[facility]['wait_time'] = 0  # wait time of the facility
            self.facilities_info[facility]['events'] = []  # a list NetworkEvent objects
            self.facilities_info[facility]['staying'] = []  # personas currently staying at the facility, engaging by their activities; a list of persona names
            self.facilities_info[facility]['waiting'] = []  # personas currently waiting at the the facility; a list of persona names
            
        # load transit schedule from transit_schedule.csv
        # transit_schedule.csv format:
        #   <metro line>, <direction>, <node name>, <arrival time>
        # Example:
        #   Metro_1, 0, Node_4, 2025-03-20 13:00:00
        self.transit_schedule = self._load_transit_schedule()
        
        #======================Initialize networkx obj==========================
        # Initialize the NetworkX graph
        self.graph = nx.DiGraph()
        
        # Add nodes to the graph
        for node_name, node_data in self.nodes_info.items():
            self.graph.add_node(node_name, **node_data)
        
        # Collect information about metro lines and stations
        # Follow Spiess and Florian (1989) transit network representation:
        #  - add artificial node for each metro line;
        #  - add artificial boarding/alighting links.
        self.pseudo_nodes = {}
        for link_name, link_data in self.links_info.items():
            if link_data['type'] == 'metro':
                start, end = link_data['endpoints']
                # Extract metro line number from link name (e.g., "metro_1_link_1" -> "1")
                line_num = link_name.split('_')[1]
                for node in [start, end]:
                    pseudo_node = f"{node}_metro_{line_num}"
                    if pseudo_node not in self.pseudo_nodes:
                        node_data = self.nodes_info[node].copy()
                        # Shift the pseudo node by exactly 1 unit for display
                        # Use different directions based on line number to avoid overlaps when displaying
                        line_int = int(line_num)
                        if line_int % 4 == 0:  # Shift lower right
                            node_data['coord'] = [node_data['coord'][0] + 1, node_data['coord'][1] + 1]
                        elif line_int % 4 == 1:  # Shift upper right
                            node_data['coord'] = [node_data['coord'][0] + 1, node_data['coord'][1] - 1]
                        elif line_int % 4 == 2:  # Shift lower left
                            node_data['coord'] = [node_data['coord'][0] - 1, node_data['coord'][1] + 1]
                        else:  # Shift up left
                            node_data['coord'] = [node_data['coord'][0] - 1, node_data['coord'][1] + 1]
                        
                        node_data['type'] = 'metro_station'
                        node_data['metro_line'] = line_num
                        self.graph.add_node(pseudo_node, **node_data)
                        self.pseudo_nodes[pseudo_node] = node_data
                                                
        # Add edges to the graph (road links and boarding/alighting links)
        for link_name, link_data in self.links_info.items():
            source, target = link_data['endpoints']
            travel_time = link_data['travel_time']
            link_type = link_data['type']
            
            if link_type == 'road':
                # Add the road edge with all attributes
                self.graph.add_edge(source, target, 
                                   name=link_name, 
                                   travel_time=travel_time,
                                   wait_time=link_data.get('wait_time', (0, 0))[0],  # Direction 0
                                   **{k: v for k, v in link_data.items() if k != 'travel_time' and k != 'wait_time'})
                
                # For bidirectional road links, add the reverse edge too
                self.graph.add_edge(target, source, 
                                   name=f"{link_name}_reverse", 
                                   travel_time=travel_time,
                                   wait_time=link_data.get('wait_time', (0, 0))[1],  # Direction 1
                                   **{k: v for k, v in link_data.items() if k != 'travel_time' and k != 'wait_time'})
            elif link_type == 'metro':
                # Get metro line for this link
                line_num = link_name.split('_')[1]
                
                # Create pseudo source and target nodes
                pseudo_source = f"{source}_metro_{line_num}"
                pseudo_target = f"{target}_metro_{line_num}"
                
                # Add the metro edge between pseudo nodes
                self.graph.add_edge(pseudo_source, pseudo_target,
                                   name=link_name,
                                   travel_time=travel_time,
                                   wait_time=0,  # Wait time moved to boarding link, traversal has no wait time!
                                   metro_line=line_num,
                                   **{k: v for k, v in link_data.items() if  k != 'travel_time' and k != 'wait_time'})
                
                # For bidirectional metro links, add the reverse edge too
                self.graph.add_edge(pseudo_target, pseudo_source,
                                   name=f"{link_name}_reverse",
                                   travel_time=travel_time,
                                   wait_time=0,  # Wait time moved to boarding link, traversal has no wait time
                                   metro_line=line_num,
                                   **{k: v for k, v in link_data.items() if  k != 'travel_time' and k != 'wait_time'})
                
                # Add boarding and alighting links if they don't already exist
                # Source boarding link
                if not self.graph.has_edge(source, pseudo_source):
                    self.graph.add_edge(source, pseudo_source,
                                       name=f"{source}_board_{line_num}",
                                       travel_time=0,
                                       wait_time=link_data.get('wait_time', (0, 0))[0],  # Direction 0: wait time
                                       type='board',
                                       metro_line=line_num,
                                       original_node=source,
                                       pseudo_node=pseudo_source,
                                       base_capacity=1000,
                                       realtime_capacity=1000)
                
                # Target boarding link
                if not self.graph.has_edge(target, pseudo_target):
                    self.graph.add_edge(target, pseudo_target,
                                       name=f"{target}_board_{line_num}",
                                       travel_time=0,
                                       wait_time=link_data.get('wait_time', (0, 0))[1],  # Direction 1: wait time
                                       type='board',
                                       metro_line=line_num,
                                       original_node=target,
                                       pseudo_node=pseudo_target,
                                       base_capacity=1000,
                                       realtime_capacity=1000)
                
                # Source alighting link
                if not self.graph.has_edge(pseudo_source, source):
                    self.graph.add_edge(pseudo_source, source,
                                       name=f"{source}_alight_{line_num}",
                                       travel_time=0,
                                       wait_time=0,
                                       type='alight',
                                       metro_line=line_num,
                                       original_node=source,
                                       pseudo_node=pseudo_source,
                                       base_capacity=1000,
                                       realtime_capacity=1000)
                
                # Target alighting link
                if not self.graph.has_edge(pseudo_target, target):
                    self.graph.add_edge(pseudo_target, target,
                                       name=f"{target}_alight_{line_num}",
                                       travel_time=0,
                                       wait_time=0,
                                       type='alight',
                                       metro_line=line_num,
                                       original_node=target,
                                       pseudo_node=pseudo_target,
                                       base_capacity=1000,
                                       realtime_capacity=1000)
        #=======================Network obj initialization end======================
        
        # Calculate all pairs shortest paths
        self.all_pairs_paths = {}
        self.all_pairs_distance = self.find_all_pairs_distance()
        
        # Load events from events.csv file if it exists
        # load events after graph created, otherwise it may report self.graph nonexistence.
        self._load_events()
        
        # generate statistics
        self._statistics()
        
        # generate descriptions
        self.nodes_description = self._generate_nodes_description()
        self.links_description = self._generate_links_description()
        self.network_description = self._generate_network_description()
        self.coverage_dict = self._generate_coverage()  # used for memory retrieval

    
    

    #============================Methods for memory retrieval========================
    def get_coverage(self, spatial_scope):
        """
        Generate spatial coverage for concept nodes
        Invoked by long term memory to compute relevance on the fly - coverage is Not stored in the concept node.
        
        Args:
            spatial_scope (list[str]): list of entities (link_name, facility_name, road_name, maze_name).
        """
        if type(spatial_scope) == str:
            spatial_scope = spatial_scope.split(',')
            
        spatial_coverage = set()
        for entity in spatial_scope:
            entity = entity.strip().lower()
            # failsafe
            if entity not in self.coverage_dict:
                pretty_print(f"Error 013: {entity} not found in coverage dict when getting coverage for spatial scope {spatial_coverage}", 2)
                continue
            spatial_coverage.update(self.coverage_dict[entity])
        return list(spatial_coverage)
        
    def _generate_coverage(self):
        """
        stored as maze instance obj;
        will be used by get_coverage method;
        
        coverage[link_name] = [link_name]
        coverage[road_name] = list of links on the road
        coverage[node_name] = the list of all links connected to this node; for temporary use
        coverage[facility_name] = the node and links connected to this node
        coverage['the town'] = list of all nodes and links on the network
        """
        coverage = {}
        coverage[self.maze_name.lower()] = []
        for link_name in self.links_info:
            road_name = link_name.split('_')[0] + "_" + link_name.split('_')[1]  # Ave_1, Metro_1, etc.
            if road_name.lower() not in coverage:
                coverage[road_name.lower()] = []
            coverage[link_name.lower()] = [link_name]
            coverage[road_name.lower()].append(link_name)
            coverage[self.maze_name.lower()].append(link_name)
            
            pt0 = self.links_info[link_name]['endpoints'][0]
            pt1 = self.links_info[link_name]['endpoints'][1]
            if pt0.lower() not in coverage:
                coverage[pt0.lower()] = []
            coverage[pt0.lower()].append(link_name)
            if pt1.lower() not in coverage:
                coverage[pt1.lower()] = []
            coverage[pt1.lower()].append(link_name)
         
        # generate coverage for a facility - the node and all links connected to the node
        for facility in self.facilities_info:
            node = self.facility2node[facility]
            coverage[self.maze_name.lower()].append(node)
            coverage[facility.lower()] = [node] + coverage[node.lower()]
        
        # ensure no duplicates
        for key, value in coverage.items():
            coverage[key] = list(set(value))
            
        return coverage
    
    
    
    
    #============================Methods for loading files========================
    def _load_transit_schedule(self):
        """
        Load transit schedule from the transit_schedule.csv file.
        
        Format:
        <metro line>, <direction>, <node name>, <arrival time>
        
        Example:
        Metro_1, 0, Node_4, 2025-03-20 13:00:00
        """
        transit_schedule = {}
        transit_file = f"{config.maze_assets_loc}/transit_schedule.csv"
        
        if not os.path.exists(transit_file):
            pretty_print(f"No transit schedule file found at {transit_file}", 1)
            return transit_schedule
        
        try:
            with open(transit_file, 'r') as f:
                csv_reader = csv.reader(f)
                loaded_entries = 0
                
                for index, row in enumerate(csv_reader):
                    if index == 0:
                        continue
                    # Skip empty rows
                    if not row or not row[0].strip():
                        continue
                    
                    # Parse the row
                    row = [item.strip() for item in row]
                    
                    # Check if we have enough elements
                    if len(row) < 4:
                        pretty_print(f"Skipping invalid transit schedule row: {row} (insufficient elements)", 2)
                        continue
                    
                    # Parse transit attributes
                    metro_line = row[0]
                    try:
                        direction = int(row[1])  # 0 or 1
                    except ValueError:
                        pretty_print(f"Skipping invalid direction in transit schedule: {row}", 2)
                        continue
                        
                    node_name = row[2]
                    arrival_time = row[3]
                    
                    # Initialize the structure if needed
                    if metro_line not in transit_schedule:
                        transit_schedule[metro_line] = {0: {}, 1: {}}
                    
                    if node_name not in transit_schedule[metro_line][direction]:
                        transit_schedule[metro_line][direction][node_name] = []
                    
                    # Add the arrival time
                    transit_schedule[metro_line][direction][node_name].append(arrival_time)
                    loaded_entries += 1
                
                # Sort all arrival times
                for metro_line in transit_schedule:
                    for direction in transit_schedule[metro_line]:
                        for node in transit_schedule[metro_line][direction]:
                            transit_schedule[metro_line][direction][node].sort()
                
                pretty_print(f"Loaded {loaded_entries} transit schedule entries from {transit_file}", 2)
                
        except Exception as e:
            pretty_print(f"Error loading transit schedule from {transit_file}: {str(e)}", 2)
        
        return transit_schedule
    

    def _load_events(self):
        """
        Load events from the events.json file.
        Node events are stored at self.nodes_info[node_name]['events']
        Link events are stored at self.links_info[link_name]['events']
        Facility events are stored at self.facilities_info[facility_name]['events']
        """        
        events_file = f"{config.maze_assets_loc}/events.json"
        
        if not os.path.exists(events_file):
            pretty_print(f"No events file found at {events_file}", 1)
            return
        
        try:
            with open(events_file, 'r') as f:
                events_data = json.load(f)
                loaded_events = 0
                
                for event_obj in events_data:
                    # Skip empty events
                    if not event_obj:
                        continue
                    
                    # Parse event attributes
                    place = event_obj.get('place')
                    
                    # Handle direction (can be None or int)
                    direction = event_obj.get('direction')
                    
                    # Handle attribute (can be None)
                    attribute = event_obj.get('attribute')
                    
                    # Handle old_value and new_value (can be None, int, or float)
                    old_value = event_obj.get('old_value')
                    new_value = event_obj.get('new_value')
                    
                    # Parse start_time and preview_time as datetime objects
                    start_time_str = event_obj.get('start_time')
                    preview_time_str = event_obj.get('preview_time')
                    try:
                        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pretty_print(f"Error 022: Invalid start_time format in event: {event_obj}", 2)
                        continue
                    try:
                        preview_time = datetime.strptime(preview_time_str, "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pretty_print(f"Error 021: Invalid preview_time format in event: {event_obj}", 2)
                        continue
                    
                    # Handle duration (convert to timedelta)
                    duration = event_obj.get('duration')
                    if duration is not None:
                        try:
                            duration = timedelta(minutes=int(duration))
                        except (ValueError, TypeError):
                            pretty_print(f"Error 020: Invalid duration in event: {event_obj}", 2)
                            duration = None
                    
                    # Get new fields
                    content = event_obj.get('content')
                    keywords = event_obj.get('keywords', [])
                    spatial_scope = event_obj.get('spatial_scope')
                    
                    # Convert time_scope strings to time objects
                    time_scope = None
                    if 'time_scope' in event_obj and event_obj['time_scope']:
                        try:
                            time_scope = []
                            for time_str in event_obj['time_scope']:
                                t = datetime.strptime(time_str, "%H:%M:%S").time()
                                time_scope.append(t)
                        except (ValueError, TypeError):
                            pretty_print(f"Error 019: Invalid time_scope format in event: {event_obj}", 2)
                            time_scope = None
                    
                    broadcast = event_obj.get('broadcast', False)
                    
                    # Create and add the event
                    event = NetworkEvent(
                        place=place,
                        direction=direction,
                        attribute=attribute,
                        old_value=old_value,
                        new_value=new_value,
                        start_time=start_time,  # Store as datetime object
                        preview_time=preview_time,
                        duration=duration,  # Store as timedelta object
                        content=content,
                        keywords=keywords,
                        spatial_scope=spatial_scope,
                        time_scope=time_scope,
                        broadcast=broadcast
                    )
                    
                    try:
                        self.add_network_event(event)
                        loaded_events += 1
                    except Exception as e:
                        pretty_print(f"Error adding event {event}: {str(e)}", 1)
                
                pretty_print(f"Loaded {loaded_events} events from {events_file}", 1)
                
        except Exception as e:
            pretty_print(f"Error 023: Error loading events from {events_file}: {str(e)}", 1)
            
    
    def add_network_event(self, event):
        """
        Add an event to network. This method only stores the event in the appropriate 
        collection without updating any network attributes. Attribute updates are handled 
        in the update() method based on current time of the simulation.
            
        Args: 
            event: NetworkEvent object
            
        Returns:: 
            None
        """
        name = event.place
        direction = event.direction
        
        if event.broadcast:
            self.broadcast_news.append(event)
            return
        
        # Check whether the name belongs to a node, link, or facility
        if name in self.nodes_info:
            # Add event to node's event list
            self.nodes_info[name]['events'].append(event)
                
        elif name in self.links_info:
            # For links, we need to determine if the event affects a specific direction
            # By default, events affect both directions if direction is None
            
            # Add event to link's event list (either both directions or specific direction)
            if direction is not None:
                self.links_info[name]['events'][direction].append(event)
            else:
                # Add to both directions
                for d in (0, 1):
                    self.links_info[name]['events'][d].append(event)
                
        elif name in self.facilities_info:
            # Add event to facility's event list
            self.facilities_info[name]['events'].append(event)
        
        # Check if this is a significant event that should be broadcast
        is_significant = self._check_if_significant_event(event)
        
        # Add to broadcast news if significant
        if is_significant:
            self.broadcast_news.append(event)
    
    
    def _check_if_significant_event(self, event):
        """
        Check if an event is significant enough to be broadcast.
        
        Args:
            event: NetworkEvent object
            
        Returns:
            bool: True if event should be broadcast, False otherwise
        """
        # Events that affect capacity drastically
        if event.attribute == 'realtime_capacity' and event.new_value is not None:
            if event.place in self.links_info:
                base_capacity = self.links_info[event.place]['base_capacity']
                if event.new_value <= base_capacity * 0.5:  # At least 50% reduction
                    return True
        
        # Events with long durations
        if event.duration and event.duration >= timedelta(minutes=120):  # 2+ hours
            return True
        
        # Events with specific critical descriptions
        critical_terms = ['accident', 'fire', 'emergency', 'disaster', 'closed', 'blocked']
        if event.content and any(term in event.content.lower() for term in critical_terms):
            return True
            
        return False
    
    
    
    #============================Methods for computing agent loc for display========================
    def get_coordinates(self, mobility_event, curr_time):
        """ 
        Compute the coordinates of the mobility event.
        A mobility event describes a persona's current movement on the network.
        
        Cases:
        1) "staying": Returns the coordinates of the facility or node where the persona is staying.
        2) "waiting":
            If waiting at a link, returns the coordinates of the source node of that link
            If waiting at a facility, returns the coordinates of the node where that facility is located
            If waiting at a node, returns the node where the persona is waiting
        3) "driving", "walking", or "riding":
            Interpolates the position along the link based on elapsed time
            Determines the direction of travel using next_node
            Accounts for walking on road links by applying the walk_time_factor
            Uses linear interpolation: position = from_coord + (to_coord - from_coord) * progress
            Clamps the progress to [0.0, 1.0] to avoid overshooting endpoints
        
        Args:
            mobility_event (dict): A mobility event.
            curr_time (datetime): The current time.
        
        Returns:
            coordinates (tuple): A tuple of coordinates.
        
        Mobility event examples:
        A persona staying at home:
        {
            'name': "Isabella Rodriguez",  # persona name
            'place': "Uptown Apartment",  # location of the event, could be link, node, facility
            'next_node': None,
            'status': "staying",  # "driving" (on a road link) / "walking" (on a a road link) / "riding" (the metro) / "waiting" (at a link or node) / "staying" (at a facility)
                                # from status we can tell the travel mode
            'start_time': datetime.strptime("2025-03-10 00:00", "%Y-%m-%d %H:%M:%S"),  # start time of the event
            'description': "staying at home",  # description of the event,
        }
        A persona driving on link:
        {
            'name': "Isabella Rodriguez",  # persona name
            'place': "St_2_link_1",  # location of the event, could be link, node, facility
            'next_node': 'Node_5',  # this determines the direction of movement
            'status': "driving",  # "driving" (on a road link) / "walking" (on a a road link) / "riding" (the metro) / "waiting" (at a link or node) / "staying" (at a facility)
                                # from status we can tell the travel mode
            'start_time': datetime.strptime("2025-03-10 00:00", "%Y-%m-%d %H:%M:%S"),  # start time of the event
            'description': "going to Gym",  # description of the event,
        }
        """
        place = mobility_event['place']
        status = mobility_event['status']
        next_node = mobility_event.get('next_node')
        start_time = mobility_event['start_time']
        
        # If staying at a facility
        if status == "staying":
            if place in self.facilities_info:
                return tuple(self.facilities_info[place]['coord'])
            elif place in self.nodes_info:
                return tuple(self.nodes_info[place]['coord'])
            else:
                raise ValueError(f"Invalid place for staying status: {place}")
        
        # If waiting at a facility or node
        elif status == "waiting":
            # Waiting at a link - return coordinates of the node that the person is staying at
            if place in self.links_info:
                link_data = self.links_info[place]
                source_node, target_node = link_data['endpoints']
                
                # Determine which node the person is at based on next_node
                if next_node == target_node:
                    # Waiting at source node to go to target
                    waiting_node = source_node
                elif next_node == source_node:
                    # Waiting at target node to go to source
                    waiting_node = target_node
                else:
                    raise ValueError(f"next_node {next_node} doesn't match link endpoints: {link_data['endpoints']}")
                    
                return tuple(self.nodes_info[waiting_node]['coord'])
            # Waiting at a facility
            elif place in self.facilities_info:
                facility_node = self.facility2node[place]
                return tuple(self.nodes_info[facility_node]['coord'])
            # Waiting at a node
            elif place in self.nodes_info:
                return tuple(self.nodes_info[place]['coord'])
            else:
                raise ValueError(f"Invalid place for waiting status: {place}")
        
        # If moving along a link (driving, walking, or riding)
        elif status in ["driving", "walking", "riding"]:
            if place not in self.links_info:
                raise ValueError(f"Invalid link for moving status: {place}")
            
            link_data = self.links_info[place]
            endpoints = link_data['endpoints']
            source_node, target_node = endpoints[0], endpoints[1]
            
            # Determine which direction we're traveling based on next_node
            if next_node == target_node:
                # Direction 0: source to target
                from_node = source_node
                to_node = target_node
            elif next_node == source_node:
                # Direction 1: target to source
                from_node = target_node
                to_node = source_node
            else:
                raise ValueError(f"next_node {next_node} doesn't match link endpoints: {endpoints}")
            
            # Get coordinates of both nodes
            from_coord = self.nodes_info[from_node]['coord']
            to_coord = self.nodes_info[to_node]['coord']
            
            # Calculate elapsed time since start of movement
            elapsed_minutes = (curr_time - start_time).total_seconds() / 60
            
            # Get travel time for interpolation
            travel_time = link_data['travel_time']
            
            # Special case: if walking on a road link, multiply travel time by walk_time_factor
            if status == "walking" and link_data['type'] == 'road':
                travel_time *= config.walk_time_factor
            
            # Calculate interpolation factor (0.0 to 1.0)
            # Clamp the value between 0 and 1 to avoid going beyond the endpoints
            progress = min(max(elapsed_minutes / travel_time, 0.0), 1.0)
            
            # Interpolate coordinates
            x = from_coord[0] + (to_coord[0] - from_coord[0]) * progress
            y = from_coord[1] + (to_coord[1] - from_coord[1]) * progress
            
            return (x, y)
        
        else:
            raise ValueError(f"Unknown status: {status}")
        
    
    
    #============================Methods for update network state========================
    def update(self, curr_time):
        """
        Update the network state.
        1) Update attributes according to active events (nodes, links, facilities)
        2) Update transit links arrival state (self.links_info[link]['arrival'])
        3) Remove expired events from the network
        4) Recalculate path information if needed due to network changes
        
        Args:
            curr_time: datetime object
        """
        # Convert current time to datetime object for comparison
        #curr_datetime = datetime.strptime(curr_time, "%Y-%m-%d %H:%M:%S")
        
        # Keep track of whether network topology changed
        network_changed = False
        
        # 1. Process active events and update attributes
        self._update_events(curr_time)
        network_changed = True  # We'll be conservative and assume changes happened
        
        # 2. Update road links and facilities wait time
        self._update_wait_time()
        
        # 3. Update transit arrivals based on schedule
        self._update_transit_arrivals(curr_time)
        
        # 4. Remove expired events from the network
        self._remove_expired_events(curr_time)
        
        # 5. If network topology changed, recalculate all pairs shortest paths
        if network_changed:
            self.all_pairs_paths = {}
            self.all_pairs_distance = self.find_all_pairs_distance()
    
    
    def _update_events(self, curr_datetime):
        """
        Update network state based on active events at the current time.
        
        Args:
            curr_datetime: Current time as datetime object
        """
        # Process node events
        for node_name, node_data in self.nodes_info.items():
            for event in node_data['events']:
                self._process_active_event(event, curr_datetime, 'node', node_name)
        
        # Process link events
        for link_name, link_data in self.links_info.items():
            # Events can affect both directions or specific directions
            for direction in [0, 1]:
                for event in link_data['events'][direction]:
                    self._process_active_event(event, curr_datetime, 'link', link_name, direction)
        
        # Process facility events
        for facility_name, facility_data in self.facilities_info.items():
            for event in facility_data['events']:
                self._process_active_event(event, curr_datetime, 'facility', facility_name)
                
    
    def _process_active_event(self, event, curr_datetime, entity_type, entity_name, direction=None):
        """
        Process an event and update network state if it's active at current time.
        
        Args:
            event: NetworkEvent object
            curr_datetime: Current time as datetime object
            entity_type: 'node', 'link', or 'facility'
            entity_name: Name of the entity
            direction: Direction (0 or 1) for link events, None otherwise
        """
        # Check if event is active (start_time <= curr_time <= start_time + duration)
        event_start = event.start_time  # Already a datetime object
        
        # Calculate event end time
        if event.duration is not None:
            event_end = event_start + event.duration  # duration is already a timedelta
        else:
            # If no duration specified, consider it a permanent event from start time
            event_end = datetime.max
        
        # Check if event is active
        is_active = event_start <= curr_datetime <= event_end
        
        if is_active and event.attribute is not None and event.new_value is not None:
            # Apply the event effect based on entity type
            if entity_type == 'node':
                # Update node attribute
                self.nodes_info[entity_name][event.attribute] = event.new_value
                self.graph.nodes[entity_name][event.attribute] = event.new_value
                
                # Also update any pseudo nodes associated with this node
                for pseudo_node in self.pseudo_nodes:
                    if pseudo_node.startswith(f"{entity_name}_metro_"):
                        self.graph.nodes[pseudo_node][event.attribute] = event.new_value
            
            elif entity_type == 'link':
                # Update link attribute for the specified direction
                if direction is not None:
                    if isinstance(self.links_info[entity_name][event.attribute], (tuple, list)):
                        # For directional attributes (stored as tuples)
                        current_values = list(self.links_info[entity_name][event.attribute])
                        current_values[direction] = event.new_value
                        self.links_info[entity_name][event.attribute] = tuple(current_values)
                    else:
                        # For non-directional attributes
                        self.links_info[entity_name][event.attribute] = event.new_value
                    
                    # Update graph edge attributes
                    if direction == 0:
                        # Direction 0: source -> target
                        source, target = self.links_info[entity_name]['endpoints']
                        if self.graph.has_edge(source, target):
                            self.graph[source][target][event.attribute] = event.new_value
                    else:
                        # Direction 1: target -> source
                        source, target = self.links_info[entity_name]['endpoints']
                        if self.graph.has_edge(target, source):
                            self.graph[target][source][event.attribute] = event.new_value
                else:
                    # Apply to both directions
                    if isinstance(self.links_info[entity_name][event.attribute], (tuple, list)):
                        self.links_info[entity_name][event.attribute] = (event.new_value, event.new_value)
                    else:
                        self.links_info[entity_name][event.attribute] = event.new_value
                    
                    # Update graph edge attributes for both directions
                    source, target = self.links_info[entity_name]['endpoints']
                    if self.graph.has_edge(source, target):
                        self.graph[source][target][event.attribute] = event.new_value
                    if self.graph.has_edge(target, source):
                        self.graph[target][source][event.attribute] = event.new_value
                    
            elif entity_type == 'facility':
                # Update facility attribute
                self.facilities_info[entity_name][event.attribute] = event.new_value

            
    
    def _remove_expired_events(self, curr_datetime):
        """
        Remove expired events from the network.
        An event is considered expired if current time > start_time + duration.
        
        Args:
            curr_datetime: Current time as datetime object
        """
        # Process node events
        for node_name, node_data in self.nodes_info.items():
            # Use list comprehension to filter out expired events
            node_data['events'] = [
                event for event in node_data['events'] 
                if not self._is_event_expired(event, curr_datetime)
            ]
        
        # Process link events
        for link_name, link_data in self.links_info.items():
            # Process events for both directions
            for direction in [0, 1]:
                link_data['events'][direction] = [
                    event for event in link_data['events'][direction]
                    if not self._is_event_expired(event, curr_datetime)
                ]
        
        # Process facility events
        for facility_name, facility_data in self.facilities_info.items():
            facility_data['events'] = [
                event for event in facility_data['events']
                if not self._is_event_expired(event, curr_datetime)
            ]


    def _is_event_expired(self, event, curr_datetime):
        """
        Check if an event is expired based on current time.
        
        Args:
            event: NetworkEvent object
            curr_datetime: Current time as datetime object
            
        Returns:
            bool: True if event is expired, False otherwise
        """
        # If event has no duration, it never expires
        if event.duration is None:
            return False
        
        # Calculate event end time (duration is already a timedelta)
        event_end = event.start_time + event.duration
        
        # Event is expired if current time is past end time
        return curr_datetime > event_end

    
    
    def _update_wait_time(self):
        """ 
        Road links wait time is updated based on the current length of the queue, realtime capacity and travel time
        Calculation:
        
        wait_time = (queue_length / realtime_capacity) * travel_time
        
        default wait time is 0
        
        Update both self.links_info and networkx graph
        """
        for link_name, link_data in self.links_info.items():
            # Only process road links
            if link_data['type'] != 'road':
                continue
                
            # Get base travel time for this link
            base_travel_time = link_data['travel_time']
            
            # Get realtime capacity for both directions
            realtime_capacity = link_data['realtime_capacity']
            
            # Calculate wait time for each direction
            new_wait_times = [0, 0]  # Initialize both directions to 0
            
            for direction in [0, 1]:               
                # Count personas driving in this direction                    
                # Count personas waiting in this direction
                if 'waiting' in link_data:
                    queue_length = len(link_data['waiting'][direction])
                
                # Get realtime capacity for this direction
                capacity = realtime_capacity[direction]
                
                # Calculate wait time using the formula: (queue_length / realtime_capacity) * travel_time
                if capacity > 0 and queue_length > 0:
                    wait_time = int((queue_length / capacity + 0.5) * base_travel_time)    
                    # 0.5 * travel time component is for the expected traversal time left
                    # Apply a reasonable upper bound to prevent extremely long wait times
                    wait_time = min(wait_time, base_travel_time * 5)  # Max 5x base travel time
                else:
                    wait_time = 0
                    
                new_wait_times[direction] = wait_time
            
            # Update the wait time in links_info
            self.links_info[link_name]['wait_time'] = [new_wait_times[0], new_wait_times[1]]
            
            # Update the wait time in the networkx graph
            endpoints = link_data['endpoints']
            source, target = endpoints[0], endpoints[1]
            
            # Update direction 0: source -> target
            if self.graph.has_edge(source, target):
                self.graph[source][target]['wait_time'] = new_wait_times[0]
                
            # Update direction 1: target -> source
            if self.graph.has_edge(target, source):
                self.graph[target][source]['wait_time'] = new_wait_times[1]
    
    
        # Update facility wait times and crowdedness
        for facility_name in self.facilities_info:
            # Calculate occupancy
            capacity = self.facilities_info[facility_name]['realtime_capacity']
            queue_length = len(self.facilities_info[facility_name]['waiting'])
            if queue_length > 0:
                wait_time = int((queue_length / capacity +  0.5) * self.facilities_info[facility_name]['average_stay'])
            else:
                wait_time = 0
            self.facilities_info[facility_name]['wait_time'] = wait_time
        

    
    
    def _update_transit_arrivals(self, curr_datetime):
        """
        Update transit arrival status based on the schedule.
        
        Args:
            curr_datetime: Current time as datetime object
        
        Note: 
        Current time span is [curr_datetime, curr_datetime + config.minutes_per_step)
        If there is a train that arrives in this time span, set the corresponding link 'arrival' property to true.
        """
        # Reset all arrival states first
        for link_name, link_data in self.links_info.items():
            if link_data['type'] == 'metro':
                link_data['arrival'] = [False, False]
        
        # Calculate the end of current time step
        end_datetime = curr_datetime + timedelta(minutes=config.minutes_per_step)
        
        # Check scheduled arrivals within the current time step
        for metro_line, line_data in self.transit_schedule.items():
            for direction in [0, 1]:
                direction_data = line_data.get(direction, {})
                
                for node_name, arrival_times in direction_data.items():
                    # Only process arrival times that fall within the current time step
                    for arrival_time_str in arrival_times:
                        arrival_time = datetime.strptime(arrival_time_str, "%Y-%m-%d %H:%M:%S")
                        
                        # Check if arrival time is within the current time step
                        if curr_datetime <= arrival_time < end_datetime:
                            # Extract metro line number (e.g., "Metro_1" -> "1")
                            line_num = metro_line.split('_')[1]
                            
                            # Find all metro links connected to this node with this metro line
                            for link_name, link_data in self.links_info.items():
                                if (link_data['type'] == 'metro' and 
                                    link_name.split('_')[1] == line_num and
                                    node_name in link_data['endpoints']):
                                    
                                    # Set the appropriate direction's arrival state to True
                                    # Note: direction 0 means the transit go from link_data['endpoints'][0] to link_data['endpoints'][1]
                                    if direction == 0 and node_name == link_data['endpoints'][0]:
                                        self.links_info[link_name]['arrival'][0] = True
                                    elif direction == 1 and node_name == link_data['endpoints'][1]:
                                        self.links_info[link_name]['arrival'][1] = True
                
    
    
    
    #============================Network computations========================
    def find_all_pairs_distance(self):
        """Find the distance between all pairs of nodes. Use road link travel time for computation."""
        # Using Floyd-Warshall algorithm to compute shortest paths between all pairs of nodes
        distance_dict = {}
        
        # For travel time, we need to sum both travel_time and wait_time attributes
        def weight_function(u, v, data):
            return data.get('travel_time', 0) + data.get('wait_time', 0)
        
        # Compute using networkx's built-in function with custom weight function
        distance_dict = dict(nx.all_pairs_dijkstra_path_length(self.graph, weight=weight_function))
        
        # Store paths too for later use
        self.all_pairs_paths = dict(nx.all_pairs_dijkstra_path(self.graph, weight=weight_function))
        
        return distance_dict
    
        
    
    #============================Utilities========================
    def same_node(self, node1, node2):
        """ 
        Check if two places are at the same node.
        """
        if (node1 not in self.nodes_info) and (node1 not in self.facilities_info):
            return False
        
        if (node2 not in self.nodes_info) and (node2 not in self.facilities_info):
            return False
        
        if node1 in self.facilities_info:
            node1 = self.facility2node[node1]
        if node2 in self.facilities_info:
            node2 = self.facility2node[node2]
        
        if  node1 == node2:
            return True
        else:
            return False
        
        
    def _statistics(self):
        """ 
        Do some statistics of the network, like counting how many roads, transit lines are there in the network.
        """
        roads = []
        transit_lines = []
        
        for link_name in self.links_info:
            road_name = link_name.split("_")[0] + '_' + link_name.split("_")[1]
            if "Metro" in road_name:
                transit_lines.append(road_name)
            else:
                roads.append(road_name)
        
        roads = list(set(roads))
        transit_lines = list(set(transit_lines))
        self.roads = ', '.join(sorted(roads))
        self.transit_lines = ', '.join(sorted(transit_lines))
        
    
    
    def _generate_nodes_description(self):
        """Generate a description of network nodes and facilities that's optimized for LLM understanding."""
        description = "NODES AND FACILITIES DESCRIPTION:\n"
        description += f"The network contains {self.num_nodes} nodes and {self.num_facilities} facilities.\n\n"
        
        # List all nodes with their facilities in a simple, consistent format
        for node_name in sorted(self.nodes_info.keys()):
            node_data = self.nodes_info[node_name]
            facilities = node_data.get('facilities', [])
            
            description += f"Node: {node_name}\n"
            if 'coord' in node_data:
                description += f"Coordinates: {node_data['coord'][0]}, {node_data['coord'][1]}\n"
                
            if facilities:
                description += f"Facilities at this node: {len(facilities)}\n"
                for facility in sorted(facilities):
                    description += f"- {facility}: {self.facilities_info[facility]['description']}\n"
            else:
                description += "This node has no facilities.\n"
            
            description += "\n"  # Add a blank line between nodes for clarity
        
        return description

    
    def _generate_links_description(self):
        """Generate a description of network links that's optimized for LLM understanding."""
        description = "LINKS DESCRIPTION:\n"
        description += f"The network contains {self.num_links} links of different types.\n\n"
        
        # Count link types for summary
        road_links = [link for link, data in self.links_info.items() if data['type'] == 'road']
        metro_links = [link for link, data in self.links_info.items() if data['type'] == 'metro']
        
        description += f"Summary: {len(road_links)} road links and {len(metro_links)} metro links.\n"
        description += "East-west road links are avenues ('Ave'). North-South road links are streets ('St').\n\n"
        
        # Road links section
        description += "ROAD LINKS:\n"
        for link_name in sorted(road_links):
            link_data = self.links_info[link_name]
            source, target = link_data['endpoints']
            
            description += f"Link: {link_name}\n"
            description += f"Connects: {source} to {target}\n"
            description += f"Travel time: {link_data['travel_time']} minutes\n"
            description += f"Base capacity: {link_data['base_capacity']}\n\n"
            #description += f"Wait time: {link_data.get('wait_time', 0)} minutes\n\n"  # Not necessary; congestion is displayed in get_congestion_info method.
        
        # Metro links section
        description += "METRO LINKS:\n"
        for link_name in sorted(metro_links):
            link_data = self.links_info[link_name]
            source, target = link_data['endpoints']
            
            description += f"Link: {link_name}\n"
            description += f"Connects: {source} to {target}\n"
            description += f"Travel time: {link_data['travel_time']} minutes\n"
            description += f"Wait time: {link_data.get('wait_time', [5, 5])[0]} minutes\n\n"
        
        # Add notes section with simple formatting
        description += "ADDITIONAL NOTES:\n"
        description += "1. Link name convention: 'Ave_<avenue number>_link_<link index>' or 'St_<street number>_link_<link index>'.\n"
        description += "2. 'travel_time' represents the vehicle or metro traversal time in minutes.\n"
        description += f"3. Walking time on a road link is {config.walk_time_factor} times the vehicle travel time.\n"
        description += "4. 'base_capacity' is the designed capacity of the link or facility.\n"
        description += "5. 'wait_time' represents the average delays due to congestion or service frequency. A road link has zero wait time when there is no congestion. Wait time due to congestion is shown in the realtime traffic state section. Metro links have constant wait time.\n"
        
        return description

    def _generate_network_description(self):
        """Generate a comprehensive network description that's optimized for LLM understanding."""        
        # Simple overview with key statistics
        description = f"""-----URBAN ENVIRONMENT OVERVIEW-----
The name of the urban environment is {self.maze_name}.
{self.maze_name} is a small urban area with a grid-based layout. {self.maze_name} features distinct areas:
- Northwest: Residential and educational area
- Central: Commercial and service area
- Southeast: Working and industrial area


-----TRANSPORTATION NETWORK-----
The transportation network has {len(self.roads)} roads and {len(self.transit_lines)} metro lines. 
 - roads: {self.roads}
 - transit lines: {self.transit_lines}
 
The transportation network is represented by a graph which consists of {self.num_nodes} nodes connected by {self.num_links} links.
There are {self.num_facilities} facilities serving various urban functions located at various nodes throughout the network.

"""
        
        # Add the detailed descriptions with clear section demarcation
        description += "---NODES AND FACILITIES DESCRIPTION SECTION START---\n"
        description += self.nodes_description
        description += "---NODES AND FACILITIES DESCRIPTION SECTION END---\n\n"
        
        description += "---LINKS DESCRIPTION SECTION START---\n"
        description += self.links_description
        description += "---LINKS DESCRIPTION SECTION END---"
        
        return description
    
    
    def get_nearby_events(self, place, vision_r=None, spatial_att_bandwidth=None):
        """
        Perceive events that take place within the vision radius of the current node.
        Returns a sorted list of (distance, event) pairs.
        
        Args:
            place: Current place (node or facility name)
            vision_r: Vision radius in travel time minutes (default: use config.vision_r)
            spatial_att_bandwidth: keep nearest spatial_att_bandwidth many events
            
        Returns:
            List of events
        """
        # Convert place to node if it's a facility
        if place in self.facilities_info:
            node = self.facility2node[place]
        else:
            node = place
            
        # Use default vision radius from config if none provided
        if vision_r is None:
            vision_r = config.vision_r
        
        if spatial_att_bandwidth is None:
            spatial_att_bandwidth = config.spatial_att_bandwidth
        
        # If node is not in the network, return empty list
        if node not in self.nodes_info:
            return []
        
        # Dictionary to store event hashes and their corresponding distances
        event_distances = {}
        
        # Get all nodes within vision radius
        nearby_nodes = {}
        for other_node in self.nodes_info:
            if other_node == node:
                nearby_nodes[other_node] = 0  # current node has distance 0
            elif other_node in self.all_pairs_distance[node] and self.all_pairs_distance[node][other_node] <= vision_r:
                nearby_nodes[other_node] = self.all_pairs_distance[node][other_node]
        
        # Process events from nearby nodes
        for n, distance in nearby_nodes.items():
            for event in self.nodes_info[n]['events']:
                # Create a hashable representation of the event
                event_hash = hash(str(event))
                # Keep the minimum distance if this event has been seen before
                if event_hash not in event_distances or distance < event_distances[event_hash][0]:
                    event_distances[event_hash] = (distance, event)
        
        # Process events from links connecting nearby nodes
        for link_name, link_data in self.links_info.items():
            src, dst = link_data['endpoints']
            
            # Check if both endpoints are within vision radius
            if src in nearby_nodes and dst in nearby_nodes:
                # Estimate distance to the link as the minimum distance to either endpoint
                link_distance = min(nearby_nodes[src], nearby_nodes[dst])
                
                # Add all events on this link
                for event in link_data['events']:
                    event_hash = hash(str(event))
                    if event_hash not in event_distances or link_distance < event_distances[event_hash][0]:
                        event_distances[event_hash] = (link_distance, event)
        
        # Process events from facilities at nearby nodes
        for facility, facility_node in self.facility2node.items():
            if facility_node in nearby_nodes:
                facility_distance = nearby_nodes[facility_node]
                
                # Add all events at this facility
                if facility in self.facilities_info:
                    for event in self.facilities_info[facility]['events']:
                        event_hash = hash(str(event))
                        if event_hash not in event_distances or facility_distance < event_distances[event_hash][0]:
                            event_distances[event_hash] = (facility_distance, event)
        
        # Convert the dictionary values to a list and sort by distance
        percept_events_list = sorted(event_distances.values(), key=itemgetter(0))
        percept_events_list = percept_events_list[:spatial_att_bandwidth]
        percept_events_list = [x[1] for x in percept_events_list]
        
        return percept_events_list

    
    def get_shortest_path(self, start_node, end_node, travel_mode="drive"):
        """
        Find the shortest path considering realtime conditions and multimodal options.
        
        Args:
            start_node (str): Starting node or facility
            end_node (str): Destination node or facility
            travel_mode (str): "drive" or "transit"
                    If "drive", persona needs to drive from start_node to end_node;
                    If "transit", persona can walk or use transit;
                    road links are considered as walking link; walking time = config.walk_time_factor x road link travel time, and there will be no wait time on walking link.
        
        Returns::
            Dictionary containing path, travel time, and mode information.
            'original_path' is a list of tuples: [(link_name, mode_name, node_name), ...]
            where:
            - link_name is the name of the link on the original network
            - mode_name is "drive"/"ride"/"walk"; "ride" means riding metro
            - node_name is the destination node of this segment
            
        We need to handle scenarios where multiple links on the same road need to be traversed sequentially to reach the next road or the final destination.
         - Road Subgraph Creation: Creates a subgraph containing only the links of the current road, which makes path finding within a road much easier.
        - Intelligent Connection Finding: For each road, it intelligently finds the connecting node to the next road by:
            Identifying all nodes that connect the current road to the next road
            Finding the closest connecting node to the current position
        - Multiple Link Traversal: Uses NetworkX's path finding to properly traverse multiple links on the same road to get from the current position to the target.
        - Better Error Handling: Provides clearer error messages when a path can't be found or when roads don't connect.
        - Bidirectional Support: Properly handles traveling in either direction on a road by adding both directions to the subgraph.
        """
        drive = (travel_mode == "drive")
        if start_node in self.facilities_info:
            start_node = self.facility2node[start_node]
        if end_node in self.facilities_info:
            end_node = self.facility2node[end_node]
        
        # Define the weight function to use both travel_time and wait_time
        def weight_function(u, v, data):
            return data.get('travel_time', 0) + data.get('wait_time', 0)
        
        # Store original values to restore later
        original_values = {}
        
        try:
            if drive:
                # If transit is not allowed, temporarily increase the weight of transit, board, and alight edges
                for u, v, data in list(self.graph.edges(data=True)):
                    if data.get('type') in ['metro', 'board', 'alight']:
                        # Store original values
                        if (u, v) not in original_values:
                            original_values[(u, v)] = {
                                'travel_time': data.get('travel_time', 0),
                                'wait_time': data.get('wait_time', 0)
                            }
                        # Disable transit links
                        self.graph[u][v]['travel_time'] = float('inf')
                        self.graph[u][v]['wait_time'] = float('inf')
            else:
                # If using transit, treat road links as walking (config.walk_time_factor x travel time, no wait time)
                for u, v, data in list(self.graph.edges(data=True)):
                    if data.get('type') == 'road':
                        # Store original values
                        if (u, v) not in original_values:
                            original_values[(u, v)] = {
                                'travel_time': data.get('travel_time', 0),
                                'wait_time': data.get('wait_time', 0)
                            }
                        # Apply walking mode: config.walk_time_factor x travel time, no wait time
                        self.graph[u][v]['travel_time'] = config.walk_time_factor * data.get('travel_time', 0)
                        self.graph[u][v]['wait_time'] = 0
            
            # Find the shortest path using Dijkstra with custom weight function
            path = nx.shortest_path(self.graph, source=start_node, target=end_node, weight=weight_function)
            
            # Calculate total travel time and collect mode information
            total_time = 0
            modes = []
            
            for i in range(len(path)-1):
                u, v = path[i], path[i+1]
                edge_data = self.graph[u][v]
                
                # Sum travel time and wait time
                trip_time = edge_data.get('travel_time', 0) + edge_data.get('wait_time', 0)
                total_time += trip_time
                
                # Add mode information
                link_type = edge_data.get('type', 'unknown')
                # If using transit and it's a road, mark it as walking
                display_mode = 'walk' if not drive and link_type == 'road' else link_type
                
                modes.append({
                    'from': u,
                    'to': v,
                    'mode': display_mode,
                    'link': edge_data.get('name', 'unknown'),
                    'travel_time': edge_data.get('travel_time', 0),
                    'wait_time': edge_data.get('wait_time', 0),
                    'total_time': trip_time
                })
            
            # Create a new representation of the path with actual link names
            original_path = []
            i = 0
            
            while i < len(path) - 1:
                curr_node = path[i]
                next_node = path[i+1]
                edge_data = self.graph[curr_node][next_node]
                edge_type = edge_data.get('type', 'unknown')
                
                # Handle road segment
                if edge_type == 'road':
                    link_name = edge_data.get('name', 'unknown')
                    # Remove '_reverse' suffix if present
                    if link_name.endswith('_reverse'):
                        link_name = link_name[:-8]
                    
                    mode = "walk" if not drive else "drive"
                    # Use the real node name, not pseudo node
                    dest_node = next_node
                    original_path.append((link_name, mode, dest_node))
                    i += 1
                    
                # Handle boarding - skip these edges
                elif edge_type == 'board':
                    i += 1
                    
                # Handle metro segment
                elif edge_type == 'metro':
                    link_name = edge_data.get('name', 'unknown')
                    # Remove '_reverse' suffix if present
                    if link_name.endswith('_reverse'):
                        link_name = link_name[:-8]
                    
                    # For destination node, we need to extract the actual node name from the pseudo node
                    # E.g., "Node_10_metro_2" -> "Node_10"
                    dest_parts = next_node.split('_metro_')
                    if len(dest_parts) > 1:
                        # This is a pseudo node, extract the base node name
                        base_node_name = dest_parts[0]
                    else:
                        # This is already a real node
                        base_node_name = next_node
                    
                    original_path.append((link_name, "ride", base_node_name))
                    i += 1
                    
                # Handle alighting - skip these edges
                elif edge_type == 'alight':
                    i += 1
                    
                # Any other edge type
                else:
                    i += 1
            
            return {
                'path': path,
                'original_path': original_path,
                'travel_time': total_time,
                'modes': modes,
            }
            
        except nx.NetworkXNoPath:
            return {
                'path': [],
                'original_path': [],
                'travel_time': float('inf'),
                'modes': [],
            }
        
        finally:
            # Restore original edge weights
            for (u, v), values in original_values.items():
                if self.graph.has_edge(u, v):  # Check if edge still exists
                    self.graph[u][v]['travel_time'] = values['travel_time']
                    self.graph[u][v]['wait_time'] = values['wait_time']
                               

    def convert_path_format(self, start_node, end_node, travel_mode, roads):
        """ 
        Input a path that have format of a list of road names, convert it to required path format.
        Includes failsafe mechanism to find alternative paths when the provided road sequence is invalid.
        
        Args:
            start_node (str): Starting node or facility
            end_node (str): Destination node or facility
            travel_mode (str): "drive" | "transit"
                    If "drive", persona needs to drive;
                    If "transit", road links are considered as walking links;
                    walking time = config.walk_time_factor x link travel time, and there will be no wait time on link.
            roads (str): a string of road names ("Ave_1", "St_2", "Metro_1") separated by comma. Road names follow the traveling order from start to end.
        
        Returns::
            A list of tuples: [(link_name, mode_name, node_name), ...]
            where:
            - link_name is the name of the link on the original network
            - mode_name is "drive"/"ride"/"walk"
            - node_name is the destination node of this segment
        """
        drive = (travel_mode == "drive")
        # Convert facility names to node names if necessary
        if start_node in self.facilities_info:
            start_node = self.facility2node[start_node]
        if end_node in self.facilities_info:
            end_node = self.facility2node[end_node]
        
        if start_node == end_node:
            pretty_print(f"Warning: start_node and end_node coincide: {start_node}, path not updated", 2)
            return []
        
        # Split the roads string into a list of road names
        if isinstance(roads, str):
            roads = roads.split(",")
        road_names = [road.strip() for road in roads]
        
        # failsafe
        # sometimes, link names are included in road_names
        road_names_tmp = []
        for road_name in road_names:
            if road_name in self.roads:
                road_names_tmp.append(road_name)
            elif road_name in self.links_info:
                    road_names_tmp.append(road_name.split("_")[0] + "_" + road_name.split("_")[1])
            else:
                # an error road name is found
                # we still add it to the list; there will be failsafe in the next step
                road_names_tmp.append(road_name)
        
        # Initialize the result path and current node
        path_result = []
        current_node = start_node
        
        # For each road, find the sequence of links to traverse
        for road_idx, road_name in enumerate(road_names):
            # Create a subgraph with only the links on this road
            subgraph = nx.DiGraph()
            
            # Find all links belonging to this road
            road_links = []
            for link_name, link_data in self.links_info.items():
                # Check if the link belongs to the specified road
                if link_name.startswith(road_name + "_link_"):
                    road_links.append((link_name, link_data))
                    
                    # Add edges to the subgraph for both directions
                    src, tgt = link_data['endpoints']
                    link_type = link_data['type']
                    
                    # Add forward direction
                    subgraph.add_edge(src, tgt, name=link_name, type=link_type)
                    
                    # Add reverse direction
                    subgraph.add_edge(tgt, src, name=link_name, type=link_type)
            
            if not road_links:
                pretty_print(f"Error 014: No links found for road {road_name}, attempting failsafe path finding", 2)
                # Failsafe: Use get_shortest_path to find a path from current_node to end_node
                shortest_path = self.get_shortest_path(current_node, end_node, travel_mode)
                
                if shortest_path['original_path']:
                    pretty_print(f"Found alternative path from {current_node} to {end_node}", 1)
                    # Add the alternative path segments to our result
                    path_result.extend(shortest_path['original_path'])
                    return path_result
                else:
                    raise ValueError(f"Error 015: No links found for road {road_name} and failsafe path finding failed", 2)
            
            # Determine the target node for this road segment
            target_node = None
            if road_idx < len(road_names) - 1:
                # This is not the last road, so we need to find where this road connects to the next one
                next_road = road_names[road_idx + 1]
                
                # Find connecting nodes between current road and next road
                connecting_nodes = set()
                for link_name, link_data in self.links_info.items():
                    if link_name.startswith(next_road + "_link_"):
                        for node in link_data['endpoints']:
                            # Check if this node is also on the current road
                            for curr_link_name, curr_link_data in road_links:
                                if node in curr_link_data['endpoints']:
                                    connecting_nodes.add(node)
                
                if not connecting_nodes:
                    pretty_print(f"Error 016: Cannot find a connection between {road_name} and {next_road}, attempting failsafe path finding", 2)
                    # Failsafe: Use get_shortest_path to find a path from current_node to end_node
                    shortest_path = self.get_shortest_path(current_node, end_node, travel_mode)
                    
                    if shortest_path['original_path']:
                        pretty_print(f"Found alternative path from {current_node} to {end_node}", 2)
                        # Add the alternative path segments to our result
                        path_result.extend(shortest_path['original_path'])
                        return path_result
                    else:
                        raise ValueError(f"Error 018: Cannot find a connection between {road_name} and {next_road} and failsafe path finding failed")
                
                # If multiple connecting nodes, choose the one closest to current_node in the subgraph
                if len(connecting_nodes) > 1:
                    closest_node = None
                    min_distance = float('inf')
                    
                    for node in connecting_nodes:
                        try:
                            # Find distance in the subgraph
                            distance = nx.shortest_path_length(subgraph, current_node, node)
                            if distance < min_distance:
                                min_distance = distance
                                closest_node = node
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            continue
                    
                    if closest_node:
                        target_node = closest_node
                    else:
                        # If we can't find a path in the subgraph, use the first connecting node
                        target_node = list(connecting_nodes)[0]
                else:
                    # Only one connecting node
                    target_node = list(connecting_nodes)[0]
            else:
                # This is the last road, so the target is the final destination
                target_node = end_node
            
            # Find the path through this road from current_node to target_node
            try:
                # Use NetworkX to find the shortest path in the subgraph
                node_path = nx.shortest_path(subgraph, current_node, target_node)
                
                # Convert the node path to link path
                for i in range(len(node_path) - 1):
                    src, tgt = node_path[i], node_path[i+1]
                    link_name = subgraph[src][tgt]['name']
                    link_type = subgraph[src][tgt]['type']
                    
                    # Determine mode based on link type and drive parameter
                    if link_type == 'road':
                        mode = "drive" if drive else "walk"
                    elif link_type == 'metro':
                        mode = "ride"
                    else:
                        mode = "unknown"
                    
                    # Add to result path
                    path_result.append((link_name, mode, tgt))
                
                # Update current_node for next iteration
                current_node = target_node
                
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pretty_print(f"Error 024: Cannot find a path on {road_name} from {current_node} to {target_node}, attempting failsafe path finding", 2)
                # Failsafe: Use get_shortest_path to find a path from current_node to end_node
                shortest_path = self.get_shortest_path(current_node, end_node, travel_mode)
                
                if shortest_path['original_path']:
                    pretty_print(f"Found alternative path from {current_node} to {end_node}")
                    # Add the alternative path segments to our result
                    path_result.extend(shortest_path['original_path'])
                    return path_result
                else:
                    raise ValueError(f"Error 025: Cannot find a path on {road_name} from {current_node} to {target_node} and failsafe path finding failed", 2)
        
        # Final check that we've reached the destination
        if current_node != end_node:
            pretty_print(f"Error 026: The provided road sequence does not lead to the destination. Ended at {current_node} instead of {end_node}, attempting failsafe path finding", 2)
            # Failsafe: Use get_shortest_path to find a path from current_node to end_node
            shortest_path = self.get_shortest_path(current_node, end_node, travel_mode)
            
            if shortest_path['original_path']:
                print(f"Error 027: Found alternative path from {current_node} to {end_node}")
                # Add the alternative path segments to our result
                path_result.extend(shortest_path['original_path'])
            else:
                raise ValueError(f"Error 028: The provided road sequence does not lead to the destination and failsafe path finding failed", 2)
        
        return path_result
    
    

    def get_road_congestion_info(self):
        """Return a string describing the congestion information (wait time) of all road links."""
        result = "Road Congestion Information (Wait Times):\n"
        #result += "=" * 50 + "\n"
        
        # Get all road links
        road_links = [(link_name, link_data) for link_name, link_data in self.links_info.items() 
                    if link_data['type'] == 'road']
        
        if not road_links:
            return result + "No road links found in the network."
        
        # Prepare data for sorting and display
        congestion_data = []
        
        for link_name, link_data in road_links:
            wait_time = link_data.get('wait_time', (0, 0))
            endpoints = link_data['endpoints']
            source, target = endpoints
            
            # Direction 0: source → target
            if wait_time[0] > 0:
                congestion_data.append({
                    'link_name': link_name,
                    'direction': 0,
                    'source': source, 
                    'target': target,
                    'wait_time': wait_time[0]
                })
            
            # Direction 1: target → source
            if wait_time[1] > 0:
                congestion_data.append({
                    'link_name': link_name,
                    'direction': 1,
                    'source': target,  # Reversed for direction 1
                    'target': source,  # Reversed for direction 1
                    'wait_time': wait_time[1]
                })
        
        # Sort by wait time (highest first) to highlight congestion
        congestion_data.sort(key=lambda x: x['wait_time'], reverse=True)
        
        # Group roads by congestion level
        severe_congestion = []
        moderate_congestion = []
        light_congestion = []
        no_congestion = len(road_links) * 2 - len(congestion_data)  # Count of links with zero wait time in both directions
        
        for link_info in congestion_data:
            link_str = f"{link_info['link_name']} (Dir {link_info['direction']}): {link_info['source']} → {link_info['target']}, Wait Time: {link_info['wait_time']} min"
            
            if link_info['wait_time'] >= 10:
                severe_congestion.append(link_str)
            elif link_info['wait_time'] >= 5:
                moderate_congestion.append(link_str)
            else:  # 0 < wait_time < 5
                light_congestion.append(link_str)
        
        # Add congestion groups to result
        if severe_congestion:
            result += "\nSevere Congestion (≥ 10 min):\n"
            result += "\n".join(severe_congestion) + "\n"
        
        if moderate_congestion:
            result += "\nModerate Congestion (5-9 min):\n"
            result += "\n".join(moderate_congestion) + "\n"
        
        if light_congestion:
            result += "\nLight Congestion (1-4 min):\n"
            result += "\n".join(light_congestion) + "\n"
        
        # Add summary statistics
        result += "\nSummary:"
        result += f"\n- Total road links: {len(road_links)} (bi-directional)"
        result += f"\n- Links with severe congestion: {len(severe_congestion)}"
        result += f"\n- Links with moderate congestion: {len(moderate_congestion)}"
        result += f"\n- Links with light congestion: {len(light_congestion)}"
        result += f"\n- Links with no congestion: {no_congestion}"
        
        # Calculate average wait time for congested directions only
        if congestion_data:
            avg_wait_time = sum(item['wait_time'] for item in congestion_data) / len(congestion_data)
            result += f"\n- Average wait time for congested directions: {avg_wait_time:.2f} min"
        
        # Calculate overall average wait time across all directions
        total_directions = len(road_links) * 2  # Each link has two directions
        if total_directions > 0:
            total_wait_time = sum(item['wait_time'] for item in congestion_data)
            overall_avg = total_wait_time / total_directions
            result += f"\n- Overall average wait time across all directions: {overall_avg:.2f} min"
        
        return result




    #==============================Visualization methods=======================================
    def get_node_positions(self):
        """
        Get node positions with proper coordinate transformation.
        For grid systems where (0,0) is in the upper left corner, we invert the y-coordinate.
        For visualization purpose.
        
        Returns::
            dict: Dictionary mapping node names to position tuples
        """
        pos = {}
        for node, data in self.graph.nodes(data=True):
            if 'coord' in data:
                x, y = data['coord']
                # Use the x coordinate as is, but invert the y coordinate
                # This places (0,0) at the upper left corner, increasing y downward
                pos[node] = (x, -y)
            else:
                # For nodes without coordinates, we'll handle them later
                pos[node] = None
                
        # If any nodes don't have coordinates, use spring layout as fallback
        missing_coords = [node for node, pos_val in pos.items() if pos_val is None]
        if missing_coords:
            # Create a subgraph of nodes missing coordinates
            subgraph = self.graph.subgraph(missing_coords)
            sub_pos = nx.spring_layout(subgraph, seed=42)
            
            # Update the position dictionary
            for node, coords in sub_pos.items():
                pos[node] = coords
                
        return pos
    

    def visualize_network(self, highlight_path=None, travel_mode="drive", show_facilities=True, show_congestion=False, node_size=300, show_pseudo_nodes=True):
        """
        Visualize the transportation network using the actual coordinates in the nodes.
        
        Args:
            highlight_path: Optional list of nodes to highlight as a path
            show_facilities: Whether to show facilities in the visualization
            show_congestion: Whether to show congestion on links
            node_size: Size of the node markers
            show_pseudo_nodes: Whether to show metro pseudo nodes
            
        Returns::
            matplotlib figure
        """
        drive = (travel_mode == "drive")
        # Create a new figure with larger size
        fig, ax = plt.subplots(figsize=(20, 16))
        
        # Set axis limits for the [0, 49] coordinate system with (0,0) at upper left
        # We flip the y-axis for display by using negative values
        ax.set_xlim(left=-5, right=55)  # Add more margins
        ax.set_ylim(bottom=-55, top=5)  # Flip y-axis with more margins
        
        # Create a copy of the graph for visualization
        G = self.graph.copy()
        
        # Get node positions with proper coordinate transformation
        pos = self.get_node_positions()
        
        # Filter nodes and edges based on show_pseudo_nodes setting
        nodes_to_draw = list(G.nodes())
        if not show_pseudo_nodes:
            nodes_to_draw = [n for n in G.nodes() if n not in self.pseudo_nodes]
        
        # Create node styling based on node type
        node_colors = []
        node_sizes = []
        node_borders = []
        
        for node in nodes_to_draw:
            # Check node type
            if node in self.pseudo_nodes:
                # Metro pseudo node
                node_colors.append('lightblue')
                node_sizes.append(node_size * 0.5)  # Smaller size for pseudo nodes
                node_borders.append('darkblue')
            elif node in self.nodes_info:
                node_colors.append('lightgray')
                node_borders.append('black')
                node_sizes.append(node_size)
        
        # Draw nodes
        nodes = nx.draw_networkx_nodes(G, pos, 
                                      nodelist=nodes_to_draw,
                                      node_size=node_sizes, 
                                      node_color=node_colors,
                                      edgecolors=node_borders)
        
        # Draw edges with different styles based on type
        road_edges = []
        metro_edges = []
        board_edges = []
        alight_edges = []
        congested_edges = []
        
        # Collect edges to draw
        edges_to_draw = []
        for u, v, d in G.edges(data=True):
            # If we're not showing pseudo nodes, skip edges to/from pseudo nodes
            if not show_pseudo_nodes and (u in self.pseudo_nodes or v in self.pseudo_nodes):
                continue
                
            edges_to_draw.append((u, v, d))
        
        # Remove duplicate edges for visualization (only show one direction for same road links)
        edges_seen = set()
        for u, v, d in edges_to_draw:
            # For road links, only show one direction
            if d.get('type') == 'road':
                edge_key = tuple(sorted([u, v]))
                if edge_key in edges_seen:
                    continue
                edges_seen.add(edge_key)
            
            # Classify edge
            if d.get('type') == 'road':
                # Check for congestion
                if show_congestion and d.get('wait_time', 0) > 0:
                    congested_edges.append((u, v))
                elif show_congestion and d.get('wait_time', 0) > 0:
                    congested_edges.append((v, u))
                else:
                    road_edges.append((u, v))
            elif d.get('type') == 'metro':
                metro_edges.append((u, v))
            elif d.get('type') == 'board':
                board_edges.append((u, v))
            elif d.get('type') == 'alight':
                alight_edges.append((u, v))
        
        # Draw different edge types with different styles
        nx.draw_networkx_edges(G, pos, edgelist=road_edges, width=2, edge_color='black', 
                               connectionstyle='arc3,rad=0.0')
        nx.draw_networkx_edges(G, pos, edgelist=metro_edges, width=2, edge_color='blue', 
                               connectionstyle='arc3,rad=0.0')
        
        # Draw boarding edges with curvy arrows
        for u, v in board_edges:
            ax.annotate("", xy=pos[v], xytext=pos[u],
                       arrowprops=dict(arrowstyle="->", color='lightblue', 
                                      connectionstyle="arc3,rad=0.3", 
                                      linewidth=1.5))
        
        # Draw alighting edges with curvy arrows
        for u, v in alight_edges:
            ax.annotate("", xy=pos[v], xytext=pos[u],
                       arrowprops=dict(arrowstyle="->", color='darkgray', 
                                      connectionstyle="arc3,rad=0.3", 
                                      linewidth=1.5))
        
        # Draw congested edges
        nx.draw_networkx_edges(G, pos, edgelist=congested_edges, width=3, edge_color='purple', 
                               connectionstyle='arc3,rad=0.0')
        
        # Highlight the path if provided
        if highlight_path and len(highlight_path) > 1:
            # Create pairs of nodes for path edges
            path_edges = list(zip(highlight_path[:-1], highlight_path[1:]))
            
            # Filter path edges if not showing pseudo nodes
            if not show_pseudo_nodes:
                path_edges = [(u, v) for u, v in path_edges 
                             if u not in self.pseudo_nodes and v not in self.pseudo_nodes]
                highlight_path = [n for n in highlight_path if n not in self.pseudo_nodes]
            
            # Tell whether it's driving or transit path
            
            # Draw path edges with different styles based on edge type
            for u, v in path_edges:
                edge_data = G.get_edge_data(u, v)
                if edge_data:
                    edge_type = edge_data.get('type', '')
                    # Line style:
                    # - dotted for walking; solid for driving; dashed for driving
                    if edge_type == 'road':
                        # Road path edge
                        line_style = 'dotted' if not drive else 'solid' 
                        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], width=4, edge_color='red', 
                                              style=line_style, arrowsize=20, connectionstyle='arc3,rad=0.0')
                    elif edge_type == 'metro':
                        # Metro path edge
                        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], width=4, edge_color='red', 
                                              style='dashed', arrowsize=20, connectionstyle='arc3,rad=0.0')
                    elif edge_type == 'board':
                        # Board path edge
                        ax.annotate("", xy=pos[v], xytext=pos[u],
                                   arrowprops=dict(arrowstyle="->", color='red', 
                                                  connectionstyle="arc3,rad=0.3", 
                                                  linewidth=3))
                    elif edge_type == 'alight':
                        # Alight path edge
                        ax.annotate("", xy=pos[v], xytext=pos[u],
                                   arrowprops=dict(arrowstyle="->", color='red', 
                                                  connectionstyle="arc3,rad=0.3", 
                                                  linewidth=3))
        
        # Draw node labels with offset to prevent truncation
        nodes_label_pos = {}
        for k, v in pos.items():
            # Calculate label position with offset
            # Adjust x offset based on node name length to prevent truncation
            x_offset = 0.6 + (0.04 * len(k))  # Longer names get more offset
            nodes_label_pos[k] = (v[0] - x_offset, v[1])
        
        # Add node labels with white background for visibility
        for node in nodes_to_draw:
            if node in pos and node in nodes_label_pos:
                x, y = nodes_label_pos[node]
                font_size = 9 if node in self.pseudo_nodes else 10
                plt.text(x, y, node, horizontalalignment='right', verticalalignment='center',
                        fontsize=font_size, fontweight='normal',
                        bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2', edgecolor='none'),
                        zorder=1000)  # High zorder to ensure labels are on top
        
        # Draw facility labels if requested
        if show_facilities:
            # Create a dictionary of facility labels for each node
            facility_labels = {}
            for facility, node in self.facility2node.items():
                if node in nodes_to_draw:  # Only include visible nodes
                    if node in facility_labels:
                        facility_labels[node] += f"\n{facility}"
                    else:
                        facility_labels[node] = facility
            
            # Position facility labels above nodes with more spacing
            facility_pos = {k: (v[0], v[1] + 1.5) for k, v in pos.items()}
            
            # Draw facility labels with a white background for better readability
            for node, label in facility_labels.items():
                if node in pos:
                    x, y = facility_pos[node]
                    plt.text(x, y, label, horizontalalignment='center', 
                            fontsize=10, color='darkred', 
                            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3', edgecolor='none'))
                
        # Create legend
        plt.figtext(0.92, 0.9, "Legend", fontsize=14, fontweight='bold')
        
        # Create node examples
        legend_y = 0.87
        x_node = 0.92
        x_text = 0.94
        
        # Normal node
        plt.figtext(x_node, legend_y, "●", color='black', fontsize=14, ha='center')
        plt.figtext(x_text, legend_y, "Regular Node", fontsize=12)
        
        # Node with facility
        legend_y -= 0.02
        plt.figtext(x_node, legend_y, "●", color='lightgray', fontsize=14, ha='center')
        plt.figtext(x_text, legend_y, "Node", fontsize=12)
        
        # Pseudo node
        legend_y -= 0.02
        plt.figtext(x_node, legend_y, "●", color='lightblue', fontsize=14, ha='center')
        plt.figtext(x_text, legend_y, "Metro Station", fontsize=12)
        
        # Path node
        legend_y -= 0.02
        plt.figtext(x_node, legend_y, "●", color='lightgreen', fontsize=16, ha='center')
        plt.figtext(x_text, legend_y, "Path Node", fontsize=12)
        
        # Edge examples
        # Road edge
        legend_y -= 0.02
        plt.figtext(x_node-0.02, legend_y, "───", color='black', fontsize=14, ha='left')
        plt.figtext(x_text, legend_y, "Road", fontsize=12)
        
        # Metro edge
        legend_y -= 0.02
        plt.figtext(x_node-0.02, legend_y, "───", color='blue', fontsize=14, ha='left')
        plt.figtext(x_text, legend_y, "Metro Line", fontsize=12)
        
        # Board edge
        legend_y -= 0.02
        plt.figtext(x_node-0.02, legend_y, "→", color='red', fontsize=14, ha='left')
        plt.figtext(x_text, legend_y, "Board", fontsize=12)
        
        # Alight edge
        legend_y -= 0.02
        plt.figtext(x_node-0.02, legend_y, "→", color='green', fontsize=14, ha='left')
        plt.figtext(x_text, legend_y, "Alight", fontsize=12)
        
        # Congested edge
        legend_y -= 0.02
        plt.figtext(x_node-0.02, legend_y, "───", color='purple', fontsize=14, ha='left')
        plt.figtext(x_text, legend_y, "Congested Road", fontsize=12)
        
        # Path edge
        legend_y -= 0.02
        plt.figtext(x_node-0.02, legend_y, "───", color='red', fontsize=14, ha='left', fontweight='bold')
        plt.figtext(x_text, legend_y, "Path", fontsize=12)
        
        # Add title
        plt.title(f"Transportation Network: {self.maze_name}", fontsize=16)
        
        # Turn off axis
        plt.axis('off')
        
        # Use tight layout to make best use of space
        plt.tight_layout()
        
        return plt
    
    
    
    def visualize_travel_times(self, start_node, show_pseudo_nodes=False, show_facilities=True):
        """
        Create a heatmap visualization showing travel times from a starting node to all other nodes.
        
        Args:
            start_node: The starting node for travel time calculation
            show_pseudo_nodes: Whether to include metro pseudo nodes in the visualization
            show_facilities: Whether to show facilities in the visualization
                
        Returns::
            matplotlib figure
        """
        if start_node not in self.all_pairs_distance:
            raise ValueError(f"Node {start_node} not found in the network")
            
        # Create a new figure with larger size
        fig, ax = plt.subplots(figsize=(20, 16))
        
        # Set axis limits for the [0, 49] coordinate system with (0,0) at upper left
        ax.set_xlim(left=-5, right=55)  # Add more margins
        ax.set_ylim(bottom=-55, top=5)  # Flip y-axis with more margins
        
        # Create a copy of the graph for visualization
        G = self.graph.copy()
        
        # Get node positions with proper coordinate transformation
        pos = self.get_node_positions()
        
        # Filter nodes based on show_pseudo_nodes setting
        nodes_to_visualize = []
        for node in G.nodes():
            if node in self.pseudo_nodes and not show_pseudo_nodes:
                continue
            nodes_to_visualize.append(node)
        
        # Get travel times from start node to all other nodes
        travel_times = self.all_pairs_distance[start_node]
        
        # Normalize travel times for color mapping
        visible_times = {node: time for node, time in travel_times.items() 
                        if node in nodes_to_visualize}
        if visible_times:
            max_time = max(visible_times.values())
        else:
            max_time = 1  # Default if no visible nodes
        
        # Create node styling based on travel time
        node_colors = []
        node_sizes = []
        node_borders = []
        
        for node in nodes_to_visualize:
            # Determine node size
            if node in self.pseudo_nodes:
                node_sizes.append(300)  # Smaller size for pseudo nodes
            else:
                node_sizes.append(600)  # Regular size for normal nodes
            
            # Determine node color based on travel time
            if node == start_node:
                node_colors.append('lightgreen')  # Start node is green
                node_borders.append('darkgreen')
            else:
                # Color from blue (near) to red (far)
                time = travel_times.get(node, max_time)
                # Normalize to range [0, 1]
                norm_time = time / max_time if max_time > 0 else 0
                # Use colormap: blue (0) to red (1)
                node_colors.append(plt.cm.coolwarm(norm_time))
                node_borders.append('black')
        
        # Draw nodes with color based on travel time
        nodes = nx.draw_networkx_nodes(G, pos, 
                                    nodelist=nodes_to_visualize,
                                    node_size=node_sizes, 
                                    node_color=node_colors,
                                    edgecolors=node_borders)
        
        # Draw edges (simplified for clarity)
        edges_to_draw = []
        for u, v, d in G.edges(data=True):
            # Skip edges to/from pseudo nodes if not showing them
            if not show_pseudo_nodes and (u in self.pseudo_nodes or v in self.pseudo_nodes):
                continue
            edges_to_draw.append((u, v))
        
        # Draw filtered edges with reduced opacity
        nx.draw_networkx_edges(G, pos, edgelist=edges_to_draw, 
                            width=1.5, edge_color='gray', alpha=0.3)
        
        # Draw node labels with offset to prevent truncation
        nodes_label_pos = {}
        for k, v in pos.items():
            if k in nodes_to_visualize:
                # Calculate label position with offset
                # Adjust x offset based on node name length to prevent truncation
                x_offset = 0.6 + (0.04 * len(k))  # Longer names get more offset
                nodes_label_pos[k] = (v[0] - x_offset, v[1])
        
        # Add node labels with white background for visibility
        for node in nodes_to_visualize:
            if node in pos and node in nodes_label_pos:
                x, y = nodes_label_pos[node]
                font_size = 18 if node in self.pseudo_nodes else 20
                plt.text(x, y, node, horizontalalignment='right', verticalalignment='center',
                        fontsize=font_size, fontweight='normal',
                        bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2', edgecolor='none'),
                        zorder=1000)  # High zorder to ensure labels are on top
        
        # Draw facility labels if requested
        if show_facilities:
            # Create a dictionary of facility labels for each node
            facility_labels = {}
            for facility, node in self.facility2node.items():
                if node in nodes_to_visualize:  # Only include visible nodes
                    if node in facility_labels:
                        facility_labels[node] += f"\n{facility}"
                    else:
                        facility_labels[node] = facility
            
            # Position facility labels above nodes with more spacing
            facility_pos = {k: (v[0] + 1.5, v[1] + 1.5) for k, v in pos.items()}
            
            # Draw facility labels with a white background for better readability
            for node, label in facility_labels.items():
                if node in pos:
                    x, y = facility_pos[node]
                    plt.text(x, y, label, horizontalalignment='center', 
                            fontsize=20, color='darkred', 
                            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3', edgecolor='none'),
                            zorder=950)
        
        # Draw travel time labels
        time_labels = {}
        for node in nodes_to_visualize:
            if node != start_node:
                # Format the travel time with 1 decimal place
                time_value = travel_times.get(node, float('inf'))
                if time_value == float('inf'):
                    time_labels[node] = "∞ min"
                else:
                    time_labels[node] = f"{time_value:.1f} min"
        
        # Position travel time labels below nodes with more space
        time_pos = {k: (v[0] + 0.5, v[1] - 2.0) for k, v in pos.items() if k in nodes_to_visualize}
        
        # Draw travel time labels with white background
        for node, label in time_labels.items():
            if node in time_pos:
                x, y = time_pos[node]
                plt.text(x, y, label, horizontalalignment='center', 
                        fontsize=18, color='black', fontweight='bold',
                        bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2', edgecolor='none'),
                        zorder=900)
        
        # Create a color bar for reference
        sm = plt.cm.ScalarMappable(cmap=plt.cm.coolwarm, norm=plt.Normalize(0, max_time))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.4, pad=0.02)
        cbar.set_label('Travel Time (minutes)', rotation=270, labelpad=20, fontsize=12)
        
        # Highlight the start node with a special marker
        plt.scatter([pos[start_node][0]], [pos[start_node][1]], 
                s=800, color='lightgreen', edgecolors='darkgreen', 
                marker='o', zorder=1001)
        
        # Add a "Start" label to the start node
        plt.text(pos[start_node][0] + 1.0, pos[start_node][1] - 1.0, f"START: {start_node}", 
                fontsize=12, fontweight='bold', color='darkgreen',
                bbox=dict(facecolor='white', alpha=0.9, boxstyle='round,pad=0.3', edgecolor='darkgreen'))
        
        # Create legend
        plt.figtext(0.92, 0.9, "Accessibility\n(start from Node_1)", fontsize=20, fontweight='bold')
        
        # Legend entries
        legend_y = 0.87
        x_node = 0.9
        x_text = 0.94
        
        # Start node
        plt.figtext(x_node, legend_y, "●", color='lightgreen', fontsize=20, ha='center')
        plt.figtext(x_text, legend_y, "Start Node", fontsize=18)
        
        # Nearby node (blue)
        legend_y -= 0.03
        plt.figtext(x_node, legend_y, "●", color='blue', fontsize=20, ha='center')
        plt.figtext(x_text, legend_y, "Nearby (Fast)", fontsize=18)
        
        # Middle distance node (purple)
        legend_y -= 0.03
        plt.figtext(x_node, legend_y, "●", color='purple', fontsize=20, ha='center')
        plt.figtext(x_text, legend_y, "Medium Distance", fontsize=18)
        
        # Far node (red)
        legend_y -= 0.03
        plt.figtext(x_node, legend_y, "●", color='red', fontsize=20, ha='center')
        plt.figtext(x_text, legend_y, "Far (Slow)", fontsize=18)
        
        # Separator line
        legend_y -= 0.03
        plt.figtext(x_text, legend_y, "───────────", fontsize=18)
        
        # Facility info 
        if show_facilities:
            legend_y -= 0.03
            plt.figtext(x_text, legend_y, "Facility Names", fontsize=18, color='darkred')
        
        # Add additional information
        legend_y -= 0.03
        plt.figtext(x_text, legend_y, "Travel Time (min)", fontsize=18)
        
        # Add title
        plt.title(f"Travel Times from {start_node}", fontsize=18)
        
        # Turn off axis
        plt.axis('off')
        
        # Use tight layout to make best use of space
        plt.tight_layout()
        
        return plt

    
    def visualize_facility_connections(self):
        """
        Create a graph showing how facilities are connected through the transportation network.
        
        Returns::
            matplotlib figure
        """
        # Create a new figure
        fig, ax = plt.subplots(figsize=(15, 12))
        
        # Create a facility graph
        facility_graph = nx.Graph()
        
        # Add facility nodes
        for facility in self.facility2node:
            facility_graph.add_node(facility)
        
        # Add edges between facilities that are directly connected
        for facility1 in self.facility2node:
            node1 = self.facility2node[facility1]
            for facility2 in self.facility2node:
                if facility1 != facility2:
                    node2 = self.facility2node[facility2]
                    # Check if nodes are connected directly
                    if self.graph.has_edge(node1, node2):
                        edge_data = self.graph[node1][node2]
                        facility_graph.add_edge(facility1, facility2, 
                                               travel_time=edge_data.get('travel_time', 0),
                                               type=edge_data.get('type', 'unknown'))
        
        # Position nodes with spring layout
        pos = nx.spring_layout(facility_graph, seed=42, k=0.5)
        
        # Draw nodes with colors based on facility type (can be customized)
        node_colors = ['#a7c957'] * facility_graph.number_of_nodes()  # Default color
        
        # Draw nodes
        nodes = nx.draw_networkx_nodes(facility_graph, pos, 
                                      node_size=800, 
                                      node_color=node_colors,
                                      edgecolors='black',
                                      alpha=0.8)
        
        # Draw edges with styles based on connection type
        edge_colors = []
        for u, v, data in facility_graph.edges(data=True):
            if data.get('type') == 'metro':
                edge_colors.append('red')
            else:
                edge_colors.append('gray')
                
        nx.draw_networkx_edges(facility_graph, pos, width=2, edge_color=edge_colors, alpha=0.6)
        
        # Draw node labels with white background for readability
        for node, (x, y) in pos.items():
            plt.text(x, y, node, horizontalalignment='center', verticalalignment='center',
                    fontsize=9, color='black', 
                    bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'))
        
        # Add title
        plt.title(f"Facility Connections in {self.maze_name}", fontsize=16)
        
        # Turn off axis
        plt.axis('off')
        
        return plt
    
    def visualize_node_grid(self):
        """
        Visualize the transportation network as a grid with coordinate system.
        Shows the 50x50 grid with (0,0) at the upper left corner.
        
        Returns:
            matplotlib figure
        """
        # Create a new figure
        fig, ax = plt.subplots(figsize=(15, 15))
        
        # Set axis limits for the [0, 49] coordinate system
        ax.set_xlim(-2, 51)
        ax.set_ylim(-51, 2)
        
        # Draw grid lines
        for i in range(0, 50, 5):  # Draw every 5th grid line for clarity
            ax.axhline(y=-i, color='lightgray', linestyle='-', alpha=0.4)
            ax.axvline(x=i, color='lightgray', linestyle='-', alpha=0.4)
            
            # Add labels for rows and columns (every 10th line)
            if i % 10 == 0:
                ax.text(50.5, -i, f"{i}", verticalalignment='center', fontsize=8)
                ax.text(i, 0.5, f"{i}", horizontalalignment='center', fontsize=8)
        
        # Get node positions with proper coordinate transformation
        pos = self.get_node_positions()
        
        # Draw nodes
        x_coords = [coord[0] for coord in pos.values()]
        y_coords = [coord[1] for coord in pos.values()]
        
        ax.scatter(x_coords, y_coords, s=150, color='blue', alpha=0.7, edgecolor='black', zorder=10)
        
        # Add node labels
        for node, coord in pos.items():
            ax.text(coord[0], coord[1], node, fontsize=8, 
                   horizontalalignment='center', verticalalignment='center', 
                   bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'),
                   zorder=11)
        
        # Draw links between nodes
        drawn_edges = set()
        for u, v, data in self.graph.edges(data=True):
            # Only process each edge once (avoid duplicates from bidirectional graph)
            edge_key = tuple(sorted([u, v]))
            if edge_key in drawn_edges:
                continue
            
            # Color based on link type
            color = 'red' if data.get('type') == 'metro' else 'gray'
            style = '--' if data.get('type') == 'metro' else '-'
            
            ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], 
                    color=color, linestyle=style, linewidth=1.5, alpha=0.7, zorder=5)
            drawn_edges.add(edge_key)
        
        # Show origin coordinates
        ax.plot(0, 0, 'ro', markersize=10)
        ax.text(1, -1, "(0,0)", fontsize=12, color='red', 
                horizontalalignment='left', verticalalignment='top')
        
        # Add title and grid labels
        ax.set_title("Transportation Network Grid View", fontsize=16)
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        
        return plt
    
    
    
    
    
    #==========================Methods for test only=================================
    def update_link_capacity(self, link_name, direction_specific=False, direction=0):
        """
        Update link congestion based on realtime capacity changes.
        
        Args:
            link_name: Name of the link
            direction_specific: Whether the update is for a specific direction
            direction: Direction (0 or 1) if direction_specific is True
        """
        if direction_specific:
            # Update congestion for specific direction
            base_capacity = self.links_info[link_name]['base_capacity']
            realtime_capacity = self.links_info[link_name]['realtime_capacity'][direction]
            
            # Simple congestion model: travel time increases as capacity decreases
            if realtime_capacity < base_capacity:
                congestion_factor = base_capacity / realtime_capacity
                base_travel_time = self.links_info[link_name]['travel_time']
                wait_time = base_travel_time * (congestion_factor - 1)
                
                # Update wait time
                if 'wait_time' not in self.links_info[link_name]:
                    self.links_info[link_name]['wait_time'] = (0, 0)
                
                wait_times = list(self.links_info[link_name]['wait_time'])
                wait_times[direction] = wait_time
                self.links_info[link_name]['wait_time'] = tuple(wait_times)
                
                # Update travel time in the graph
                if direction == 0:
                    source, target = self.links_info[link_name]['endpoints']
                    if self.graph.has_edge(source, target):
                        self.graph[source][target]['travel_time'] = base_travel_time + wait_time
                else:
                    source, target = self.links_info[link_name]['endpoints']
                    if self.graph.has_edge(target, source):
                        self.graph[target][source]['travel_time'] = base_travel_time + wait_time
        else:
            # Update congestion for both directions
            base_capacity = self.links_info[link_name]['base_capacity']
            
            for dir_idx in [0, 1]:
                realtime_capacity = self.links_info[link_name]['realtime_capacity'][dir_idx]
                
                # Simple congestion model: travel time increases as capacity decreases
                if realtime_capacity < base_capacity:
                    congestion_factor = base_capacity / realtime_capacity
                    base_travel_time = self.links_info[link_name]['travel_time']
                    wait_time = base_travel_time * (congestion_factor - 1)
                    
                    # Update wait time
                    if 'wait_time' not in self.links_info[link_name]:
                        self.links_info[link_name]['wait_time'] = (0, 0)
                    
                    wait_times = list(self.links_info[link_name]['wait_time'])
                    wait_times[dir_idx] = wait_time
                    self.links_info[link_name]['wait_time'] = tuple(wait_times)
                    
                    # Update travel time in the graph
                    if dir_idx == 0:
                        source, target = self.links_info[link_name]['endpoints']
                        if self.graph.has_edge(source, target):
                            self.graph[source][target]['travel_time'] = base_travel_time + wait_time
                    else:
                        source, target = self.links_info[link_name]['endpoints']
                        if self.graph.has_edge(target, source):
                            self.graph[target][source]['travel_time'] = base_travel_time + wait_time
    
    
    def update_link_wait_time(self, link_name, new_value, direction_specific=False, direction=0):
        """
        Update link wait time.
        
        Args:
            link_name: Name of the link
            new_value: New wait time value
            direction_specific: Whether the update is for a specific direction
            direction: Direction (0 or 1) if direction_specific is True
        """
        if direction_specific:
            # Update wait time for specific direction
            wait_times = list(self.links_info[link_name]['wait_time'])
            wait_times[direction] = new_value
            self.links_info[link_name]['wait_time'] = tuple(wait_times)
            
            # Update graph edge wait time
            if direction == 0:
                source, target = self.links_info[link_name]['endpoints']
                if self.graph.has_edge(source, target):
                    self.graph[source][target]['wait_time'] = new_value
            else:
                source, target = self.links_info[link_name]['endpoints']
                if self.graph.has_edge(target, source):
                    self.graph[target][source]['wait_time'] = new_value
                    
            # For metro links, also update boarding links
            if self.links_info[link_name]['type'] == 'metro':
                line_num = link_name.split('_')[1]
                source, target = self.links_info[link_name]['endpoints']
                node = source if direction == 0 else target
                
                # Update boarding link wait time
                for u, v, data in self.graph.edges(data=True):
                    if (data.get('type') == 'board' and 
                        data.get('metro_line') == line_num and 
                        data.get('original_node') == node):
                        self.graph[u][v]['wait_time'] = new_value
        else:
            # Update wait time for both directions
            self.links_info[link_name]['wait_time'] = (new_value, new_value)
            
            # Update graph edge wait times
            source, target = self.links_info[link_name]['endpoints']
            if self.graph.has_edge(source, target):
                self.graph[source][target]['wait_time'] = new_value
            if self.graph.has_edge(target, source):
                self.graph[target][source]['wait_time'] = new_value
            
            # For metro links, also update boarding links
            if self.links_info[link_name]['type'] == 'metro':
                line_num = link_name.split('_')[1]
                source, target = self.links_info[link_name]['endpoints']
                
                # Update boarding links wait time for both nodes
                for node in [source, target]:
                    for u, v, data in self.graph.edges(data=True):
                        if (data.get('type') == 'board' and 
                            data.get('metro_line') == line_num and 
                            data.get('original_node') == node):
                            self.graph[u][v]['wait_time'] = new_value
    
    
    
if __name__ == "__main__":
    maze = Maze("the town")
    print("Maze initialized successfully")
    #print(maze.nodes_description)
    #print()
    #print(maze.links_description)
    #print()
    print(maze.network_description)
    
    plt.figure()
    maze.visualize_node_grid()
    plt.savefig(f"{config.maze_assets_loc}/node_grid.png", dpi=150, bbox_inches='tight')
    
    maze.update(datetime.strptime("2025-03-10 08:30:00", "%Y-%m-%d %H:%M:%S"))
    
    # Test 1: Normal conditions driving path finding
    print("\n=== TEST 1: Default road conditions ===")
    # Example: Find shortest path
    start_node = 'Node_1'
    end_node = 'Node_3'
    path_info = maze.get_shortest_path(start_node, end_node, travel_mode="drive")
    print(f"Shortest path from {start_node} to {end_node}:")
    print(f"  Nodes: {path_info['path']}")
    print(f"  Travel time: {path_info['travel_time']} minutes")
    
    # Create multiple visualizations
    plt.figure(1)
    maze.visualize_network(highlight_path=path_info['path'], show_congestion=True, travel_mode="drive")
    plt.savefig(f"{config.maze_assets_loc}/network_visualization_test1.png", dpi=150, bbox_inches='tight')
    print("Network visualization saved to network_visualization.png")
    
    plt.figure(2)
    maze.visualize_travel_times(start_node)
    plt.savefig(f"{config.maze_assets_loc}/travel_times.png", dpi=150, bbox_inches='tight')
    print("Travel times visualization saved to travel_times.png")
    
    plt.figure(3)
    maze.visualize_facility_connections()
    plt.savefig(f"{config.maze_assets_loc}/facility_connections.png", dpi=150, bbox_inches='tight')
    print("Facility connections visualization saved to facility_connections.png")
    
    print(f"  Complete path: {path_info['path']}")
    print(f"  Simplified path: {path_info['original_path']}")
    

    # Test 2: Transit path finding
    print("\n=== TEST 2: Transit path finding test===")
    plt.figure(4)
    path_info = maze.get_shortest_path(start_node, end_node, travel_mode="transit")
    maze.visualize_network(highlight_path=path_info['path'], show_congestion=True, travel_mode="drive")
    plt.savefig(f"{config.maze_assets_loc}/network_visualization_test2.png", dpi=150, bbox_inches='tight')
    print("Network visualization saved to network_visualization.png")
    
    print(f"  Complete path: {path_info['path']}")
    print(f"  Simplified path: {path_info['original_path']}")
    
        
    # Test 3: High road congestion
    print("\n=== TEST 3: Road congestion test===")
    links = ['St_2_link_2']
    wait_times = [50]
    for link, wait_time in zip(links, wait_times):
        maze.update_link_wait_time(link, wait_time)
    
    # Find shortest path with congested roads
    start_node = 'Node_1'
    end_node = 'Node_3'
    path_info = maze.get_shortest_path(start_node, end_node, travel_mode="drive")
    print(f"Shortest path with road congestion from {start_node} to {end_node}:")
    print(f"  Complete path: {path_info['path']}")
    print(f"  Simplified path: {path_info['original_path']}")
    print(f"  Total travel time: {path_info['travel_time']} minutes")
    maze.visualize_network(highlight_path=path_info['path'], show_congestion=True, travel_mode="drive")
    plt.savefig(f"{config.maze_assets_loc}/network_visualization_test3.png", dpi=150, bbox_inches='tight')
    print("Network visualization saved to network_visualization.png")
    
    # Test 4: Get road congestion
    print("\n=== TEST 4: Get road congestion ===")
    print(maze.get_road_congestion_info())
    
    # Test 5: convert path format
    print("\n=== TEST 5: Convert path format ===")
    print(maze.convert_path_format('Node_1', 'Node_11', 'drive', 'St_2, Ave_3'))
    
    # Test 6: convert path format (when path is erroneous)
    print("\n=== TEST 6: convert path format ===")
    print(maze.convert_path_format('Node_1', 'Node_2', 'transit', 'St_2, Metro_1, Ave_3'))
    