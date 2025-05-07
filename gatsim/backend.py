"""
File: backend.py
Description: This is the main program for running Generative-agent transport simulation (GATSim). 
"""
import json
import os
import random
from datetime import datetime, timedelta
import time
import shutil
import traceback
import re
import argparse
import copy
from gatsim import config
from gatsim.utils import parse_command, pretty_print, copyanything, clean_folder
from gatsim.map.maze import Maze
from gatsim.agent.llm_modules.run_prompt import generate_importance_score
from gatsim.agent.memory_modules.long_term_memory import ConceptNode
from gatsim.agent.persona import Persona, initialize_population


random.seed(0)

""" 
# Terminology
 - node: transportation network graph node;
 - link: transportation network graph link;
 - location: node or link, namely a transportation network graph entity;
 - facility: a place for activity, like Office, Gym;
 - place: location or facility, a maze entity;
 - step: the total number of steps the simulation has taken
 - count: the number of steps that the simulation will take for this run. A count down.


# Persona activity plan
 - persona.st_mem.activity_facility: the target facility where activity take places
 - persona.st_mem.activity_departure_time: time to departure for the activity
 - persona.st_mem.activity_duration: planned activity duration (including travel time; once time reached, persona need to decide next activity)
 - persona.st_mem.reflect_every: how frequently persona can update his or her activity plan
 - persona.st_mem.travel_mode: "drive" or "transit"
 - persona.st_mem.activity_description: string description of the activity


# Persona mobility tracking
There are redundancies on mobility tracking.
 - Persona will remember where he or she is in the short term memory to facilitate personal cognitive process;
 - Persona movements is also tracked by backend server to simulate traffic flow;
 - Persona movements are also tracked by network (maze class) to facilitate realtime state update (say, update congestion level; impose capacity constraints);

    1) Persona current activity in persona memory
    - persona.st_mem.planned_path: a list with elements like (next_link, next_mode, next_node), guiding how persona should move on the maze transportation network;
        the first element is popped when persona is entering the next_link; so next_mode/next_node information of this first element also got transferred to mobility event;
    - persona.st_mem.curr_place: current place of the persona on the transportation network
    - persona.st_mem.curr_status: description of what the persona is doing now (say, waiting on link, staying in a facility ...) 

    2) persona mobility tracking in backend simulator
    - we will use mobility events to track persona movements
    - backend_server.mobility_events is a dict keeping track of persona movements
    - Each persona has exactly one mobility event
    - Mobility event is created at the start of the simulation, and updated for each run step.
    - A mobility event is a dict, with keys:
        'name' (str): persona name
        'place' (str): node, link, or facility name
        'next_node' (str): next node of the persona if on link; None if on a node or facility
        'status' (str): "driving" (on a road link) / "walking" (on a a road link) / "riding" (the train) / "waiting" (at a link or node or facility) / "staying" (at a facility)
        'start_time' (datetime): start time of the event
        'description' (str): description of the event
        'moved' (bool): whether this persona has already been moved in this run step,

    Examples: a persona staying at home
    self.mobility_events["Isabella Rodriguez"] = {
                    'name': "Isabella Rodriguez",  # persona name
                    'place': "Uptown Apartment",  # location of the event, could be link, node, facility
                    'next_node': None,
                    'status': "staying",  # "driving" (on a road link) / "walking" (on a a road link) / "riding" (the train) / "waiting" (at a link or node) / "staying" (at a facility)
                                        # from status we can tell the travel mode
                    'start_time': datetime.strptime("2025-03-10 00:00", "%Y-%m-%d %H:%M:%S"),  # start time of the event
                    'description': "staying at home",  # description of the event,
                    'moved': False,  # whether this persona has already been moved in this run step,
    }
    Examples:  a persona driving on link
    self.mobility_events["Isabella Rodriguez"] = {
                    'name': "Isabella Rodriguez",  # persona name
                    'place': "St_2_link_1",  # location of the event, could be link, node, facility
                    'next_node': 'Node_5',  # this determines the direction of movement
                    'status': "driving",  # "driving" (on a road link) / "walking" (on a a road link) / "riding" (the train) / "waiting" (at a link or node) / "staying" (at a facility)
                                        # from status we can tell the travel mode
                    'start_time': datetime.strptime("2025-03-10 00:00", "%Y-%m-%d %H:%M:%S"),  # start time of the event
                    'description': "going to Gym",  # description of the event,
                    'moved': True,  # whether this persona has already been moved in this run step,
    }

    3) Persona mobility tracking on network
    we maintain queue lists at nodes, links, and facilities
    - queue lists (list of persona names) are stored on the network;
    - queue lists are updated with mobility events update;
    - mobility events and queue lists are all stored;
    - queue lists includes:
        - maze.links_info[link]['driving'][i]  
            # number of moving personas on a road link with direction i (i = 0, 1)
            # it's a list of persona names; 
        - maze.links_info[link]['riding'][i]
            # number of moving personas on a metro link with direction i (i = 0, 1)
            # it's a list of persona names; 
        - maze.links_info[link]['waiting'][i] 
            # if the link is road link, it means the number of personas waiting to drive through the road link for direction i (i = 0, 1)
            # if the link is metro link, it means the number of personas waiting to board the metro link for direction i (i = 0, 1)
            # a list of persona names
        - maze.nodes_info[node]['waiting']  
            # number of personas waiting at a node to enter next link or facility
        - maze.facilities_info[facility]['staying']
            # number of personas staying in the facility, engaged in their planned activities;
        - maze.facilities_info[facility]['waiting']
            # number of personas waiting at the facility
    

# Simulation storage
Simulation  can stored and reloaded.
File structure:
gatsim/storage/simulation_name/
    ├── meta.json
    ├── personas/
    │    ├── persona_name/
    │    │      ├──short_term_memory.json
    │    │      └──long_term_memory.json
    │    └── ...
    └── movements/
         ├── 0.json
         └── ...

Note: Travel experiences are added to persona long term memory (lt_mem) in backend script.
See "#===Add trip experience to memory===" part of code


# Cache
Simulation storage is updated at the end of each simulation step; they are used for logging and reloading the simulation. All chats, all plans, all reflections are stored.
V.S. Cache files (for movements, messages) are updated immediately when movements, chatting, reflection happened within a simulation step; 
They are used for dynamic visualization. Only current ones are stored in cache. And they are cleaned at the end of each simulation step. 


# Notes about travel mode:
<link_type> of link in network: road/metro, where "road" means persona can drive or walk through the road link; "metro" means persona can only ride train through the metro link;
<travel_mode> in activity plan: drive/transit, where "transit" means persona can walk or use transit to reach the activity facility;
link traversing mode (path component): drive/walk/ride, where "walk" means walking through the road link, "ride" means riding train through the metro link.
link queue types: driving/walking/riding/waiting


# Notes on visualization
gatsim/cache/ folder is used for backend to store current information for visualizing dynamic data by frontend.
This cache folder is updated during each simulation step.
 - gatsim/cache/curr_meta.json stores current step meta information.
 - gatsim/cache/curr_plans.json stores current persona plans.
 - gatsim/cache/curr_messages.json stores current persona chats and reflection information.
 - gatsim/cache/curr_movements.json stores current step movements.

"""

        
class BackendServer: 
    def __init__(self, fork_name, simulation_name):
        """ 
        Backend server for the simulation.
        
        Args:
            fork_name (str): Name of the fork.
            simulation_name (str): Name of the simulation.
            
        Returns:
            None
        """    
        if fork_name:  # if fork_name is not empty, load the fork
            print('>>> Creating fork simulation...')
            self.fork_name = fork_name
            fork_folder = f"{config.persona_storage}/{self.fork_name}"

            # <simulation_name> indicates our current simulation. The first step here is to  
            # copy everything that's in <fork_name>, but edit its meta.json's fork variable. 
            self.simulation_name = simulation_name
            simulation_folder = f"{config.persona_storage}/{self.simulation_name}"
            self.simulation_folder = simulation_folder
            copyanything(fork_folder, simulation_folder)

            with open(f"{simulation_folder}/meta.json") as json_file:  
                simulation_meta = json.load(json_file)

            with open(f"{simulation_folder}/meta.json", "w") as outfile: 
                # complete the fork variable in meta.json
                simulation_meta["fork_name"] = fork_name
                outfile.write(json.dumps(simulation_meta, indent=4))

            # LOADING SIMU GLOBAL VARIABLES
            self.start_date = datetime.strptime(simulation_meta['start_date'], "%Y-%m-%d %H:%M:%S")
            
            # <curr_time> is the datetime instance that indicates the game's current time. 
            # This gets incremented by <minutes_per_step> amount everytime the world
            # progresses (that is, everytime curr_env_file is recieved). 
            self.curr_time = datetime.strptime(simulation_meta['curr_time'], "%Y-%m-%d %H:%M:%S")
            # <minutes_per_step> denotes the number of seconds in game time that each 
            # step moves foward. 
            self.minutes_per_step = simulation_meta['minutes_per_step']
            
            # <maze> is the main Maze instance. Note that we pass in the maze_name
            # (e.g., "double_studio") to instantiate Maze. 
            # e.g., Maze("double_studio")
            self.maze = Maze(simulation_meta['maze_name'])
            
            # <step> denotes the number of steps that our game has taken. A step here
            # literally translates to the number of moves our personas made in terms of the number of tiles. 
            self.step = simulation_meta['step']

            # SETTING UP PERSONAS
            self.population = dict()
            for persona_name in simulation_meta['persona_names']:
                persona_folder = f"{simulation_folder}/personas/{persona_name}"
                self.population[persona_name] = Persona(persona_name, persona_folder)
                self.population[persona_name].load(persona_folder)
            
            # load mobility_events and queue_lists from f"{simulation_folder}/movements/{str(self.step)}.json"
            movements_file = f"{self.simulation_folder}/movements/{str(self.step)}.json"
            if os.path.exists(movements_file):
                try:
                    with open(movements_file, 'r') as f:
                        movements_data = json.load(f)
                        
                    # Load mobility events
                    self.mobility_events = {}
                    for persona_name, event in movements_data.get('mobility_events', {}).items():
                        # Convert string timestamps back to datetime objects
                        if 'start_time' in event and isinstance(event['start_time'], str):
                            event['start_time'] = datetime.strptime(event['start_time'], "%Y-%m-%d %H:%M:%S")
                        
                        # Add the 'moved' flag which isn't stored in the saved file
                        event['moved'] = False
                        
                        # Store the event
                        self.mobility_events[persona_name] = event
                    
                    # Load queue lists
                    queues = movements_data.get('queues', {})
                    
                    # Reset all queues first to ensure clean state
                    for node_name in self.maze.nodes_info:
                        self.maze.nodes_info[node_name]['waiting'] = []
                        
                    for facility_name, facility_data in self.maze.facilities_info.items():
                        facility_data['staying'] = []
                        facility_data['waiting'] = []
                        
                    for link_name, link_data in self.maze.links_info.items():
                        if 'driving' in link_data:
                            link_data['driving'] = [[], []]
                        if 'riding' in link_data:
                            link_data['riding'] = [[], []]
                        if 'walking' in link_data:
                            link_data['walking'] = [[], []]
                        if 'waiting' in link_data:
                            link_data['waiting'] = [[], []]
                    
                    # Now load the queues
                    for place_name, queue_data in queues.items():
                        # Handle facilities
                        if place_name in self.maze.facilities_info:
                            if 'staying' in queue_data:
                                self.maze.facilities_info[place_name]['staying'] = queue_data['staying']
                            if 'waiting' in queue_data:
                                self.maze.facilities_info[place_name]['waiting'] = queue_data['waiting']
                        
                        # Handle nodes
                        elif place_name in self.maze.nodes_info:
                            if 'waiting' in queue_data:
                                self.maze.nodes_info[place_name]['waiting'] = queue_data['waiting']
                        
                        # Handle links - these are more complex because of directional queues
                        elif place_name in self.maze.links_info:
                            link_data = self.maze.links_info[place_name]
                            
                            # For simplicity in storage, link queues were stored without direction
                            # We need to put them back in the correct direction based on mobility events
                            for queue_type in ['driving', 'riding', 'walking', 'waiting']:
                                if queue_type in queue_data and queue_type in link_data:
                                    for persona_name in queue_data[queue_type]:
                                        if persona_name in self.mobility_events:
                                            # Get the direction from mobility event
                                            event = self.mobility_events[persona_name]
                                            if 'next_node' in event and event['next_node']:
                                                next_node = event['next_node']
                                                # Determine direction
                                                endpoints = link_data['endpoints']
                                                direction = 1 if next_node == endpoints[0] else 0
                                                link_data[queue_type][direction].append(persona_name)
                    
                    pretty_print(f"Loaded mobility events and queue lists from {movements_file}", 1)
                except Exception as e:
                    pretty_print(f"Error loading movements data: {str(e)}", 1)
                    traceback.print_exc()
                    # Initialize from scratch if loading fails
                    self.mobility_events = {}
            else:
                pretty_print(f"No movements file found at {movements_file}, initializing from scratch", 1)
                # Initialize from scratch
                self.mobility_events = {}
            
        else:  # create a new simulation from scratch
            # mainly load settings from config files
            print('>>> Creating a new simulation by loading population and config files...')
            simulation_meta = dict()
            self.fork_name = None
            simulation_meta['fork_name'] = None
            self.simulation_name = simulation_name
            simulation_meta['simulation_name'] = self.simulation_name
            simulation_folder = f"{config.persona_storage}/{self.simulation_name}"
            self.simulation_folder = simulation_folder
            os.makedirs(simulation_folder, exist_ok=True)
            
            # load data from config file
            self.start_date = datetime.strptime(config.start_date, "%Y-%m-%d %H:%M:%S")
            simulation_meta["start_date"] = config.start_date
            self.curr_time = datetime.strptime(config.start_date, "%Y-%m-%d %H:%M:%S")
            simulation_meta['curr_time'] = config.start_date
            self.minutes_per_step = config.minutes_per_step
            simulation_meta['minutes_per_step'] = config.minutes_per_step
            self.maze = Maze(config.maze_name)
            simulation_meta['maze_name'] = config.maze_name
            self.step = 0
            simulation_meta['step'] = 0

            # create population
            simulation_folder = f"{config.persona_storage}/{self.simulation_name}"
            self.population = initialize_population(f'{config.agent_path}/population_info.json', simulation_folder)
            simulation_meta['persona_names'] = list(self.population.keys())
            
            # initialize cache
            curr_movements_f = f"{config.cache}/curr_movements.json"
            curr_movements = dict()
            curr_movements['mobility_events'] = dict()
            curr_movements['meta'] = dict()
            curr_movements['queues'] = dict()
            for persona_name in self.population.keys():
                curr_movements['mobility_events'][persona_name] = None
            with open(curr_movements_f, "w") as f:
                json.dump(curr_movements, f, indent=4)
            
            # initialize mobility events
            self.mobility_events = {}
            for persona_name in simulation_meta['persona_names']:
                self._initialize_mobility_events(persona_name, generate_random_plan=False)
                # Only set generate_random_plan=True if you want to test backend server - initialize personas with random activity plans
            self.save()  # save the newly created simulation
                  
        # <server_sleep> denotes the amount of time that our while loop rests each cycle; this is to not kill our machine. 
        self.server_sleep = config.server_sleep
        


    def _initialize_mobility_events(self, persona_name, generate_random_plan=False):
        """
        Initialize backend server movement plans when creating a new simulation
        Personas all start with staying at home.
        
        Args:
            persona_name (str): Name of the persona to initialize
            generate_random_plan (bool): true if random persona plan needs to be generated; only for backend server testing
        """
        persona = self.population[persona_name]
        
        # Get home_facility
        home_facility = persona.st_mem.home_facility
        persona.st_mem.curr_place = home_facility
        
        if generate_random_plan:
            # Randomly select a destination facility (not the same as home)
            available_facilities = list(self.maze.facilities_info.keys())
            if home_facility in available_facilities:
                available_facilities.remove(home_facility)
            
            target_facility = random.choice(available_facilities)
            
            # Set the target facility in persona's memory
            persona.st_mem.activity_facility = target_facility
        
            # Set a departure time in the near future (10-30 minutes)
            departure_minutes = 0  #random.randint(10, 30)
            persona.st_mem.activity_departure_time = self.curr_time + timedelta(minutes=departure_minutes)
        
            # Determine if the persona will use transit
            travel_mode = "drive" if random.random() < 0.4 else "transit" # 40% chance to drive
        
            # Find the source and target nodes for path planning
            source_node = self.maze.facility2node[home_facility]
            target_node = self.maze.facility2node[target_facility]
        
            # Find a path from home to the destination
            path_info = self.maze.get_shortest_path(source_node, target_node, travel_mode=travel_mode)
        
            # Save the path to the persona's memory
            persona.st_mem.planned_path = path_info['original_path']
            persona.st_mem.reflect_every = None
            persona.st_mem.activity_duration = timedelta(minutes=120)
            persona.st_mem.activity_description = f"{persona} is going to {persona.st_mem.activity_facility}"
        
        # Fix: Initialize facility's 'staying' list if it doesn't exist
        if 'staying' not in self.maze.facilities_info[home_facility]:
            self.maze.facilities_info[home_facility]['staying'] = []
            
        # Add persona to staying list if not already there
        if persona_name not in self.maze.facilities_info[home_facility]['staying']:
            self.maze.facilities_info[home_facility]['staying'].append(persona_name)
        
        # Update mobility events
        self.mobility_events[persona_name] = {
            'name': persona_name,  # Fix: Use persona_name instead of persona object
            'place': home_facility,
            'next_node': None,
            'status': 'staying',
            'start_time': self.curr_time,
            'description': 'staying at home',
            'moved': False
        }
        
        # Update coordinates of the event
        coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
        self.mobility_events[persona_name]['coord'] = coord
                
        # update cache file for frontend visualization (movements.json)
        json_path = 'gatsim/cache/curr_movements.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['mobility_events'][persona_name] = {
            'name': persona_name,
            'place': home_facility,
            'next_node': None,
            'status': 'staying',
            'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
            'description': 'staying at home',
            'moved': False,
            'coord': coord
        }
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        # Fix: Don't add to nonexistent 'staying' key in facilities_info
        # self.maze.facilities_info['staying'].append(persona_name)
        if generate_random_plan:
            pretty_print(f"Initialized {persona_name} with plan to go from {home_facility} to {target_facility} at {persona.st_mem.activity_departure_time.strftime('%H:%M')} using {'drive' if travel_mode else 'transit'}", 1)



    def save(self): 
        """
        Save all simulation progress, including network state, personas states, and simulation meta data
        Saves all relevant data to the designated memory directory.
        """
        # Save simulation meta information.
        simulation_meta_f = f"{self.simulation_folder}/meta.json"
        simulation_meta = dict() 
        simulation_meta["fork_name"] = self.fork_name
        simulation_meta["simulation_name"] = self.simulation_name
        simulation_meta["start_date"] = self.start_date.strftime("%Y-%m-%d %H:%M:%S")
        simulation_meta["curr_time"] = self.curr_time.strftime("%Y-%m-%d %H:%M:%S")
        simulation_meta["minutes_per_step"] = self.minutes_per_step
        simulation_meta["maze_name"] = self.maze.maze_name
        simulation_meta["persona_names"] = list(self.population.keys())
        simulation_meta["step"] = self.step
        with open(simulation_meta_f, "w") as f:
            json.dump(simulation_meta, f, indent=4)

        # Save the personas
        for persona_name, persona in self.population.items(): 
            persona.save()

        # save mobility events and network queue lists.
        os.makedirs(f"{self.simulation_folder}/movements", exist_ok=True)
        movement_file = f"{self.simulation_folder}/movements/{str(self.step)}.json"
        movements = {"meta": {}, "mobility_events": {},  "queues": {}}
        """
        Example: 
        movements  = {
            "meta": {
                "curr_time": "2023-03-10, 02:30:00"
            },
            "mobility_events": {
                "Isabella Rodriguez": {
                    'name':"Isabella Rodriguez",  # persona name
                    'place':"Uptown Apartment",  # location of the event, could be link, node, facility
                    'status':"staying",  # "driving" (on a road link) / "walking" (on a a road link) / "riding" (the train) / "waiting" (at a link or node) / "staying" (at a facility)
                                        # from status we can tell the travel mode
                    'next_node':None,
                    'start_time':"2025-03-10 00:00",  # start time of the event, format: "%Y-%m-%d %H:%M:%S"
                    'description':"staying at home",  # description of the event
                }
            },
            "queue_lists": {
                "Uptown Apartment": {
                    "staying" = ["Isabella Rodriguez"]
                },
                "Ave_1_link_2": {
                    "driving" = ["Klaus Mueller"],
                    "waiting" = [],
                    "walking" = []
                }
            }
        """
        movements["meta"]["curr_time"] = self.curr_time.strftime("%Y-%m-%d %H:%M:%S")
        # Fix: Fill in mobility_events
        for persona_name, event in self.mobility_events.items():
            # Create a serializable copy of the event
            serialized_event = event.copy()
            
            # Convert persona object to name string if needed
            if isinstance(serialized_event['name'], object) and not isinstance(serialized_event['name'], str):
                serialized_event['name'] = persona_name
                
            # Convert datetime to string
            if isinstance(serialized_event['start_time'], datetime):
                serialized_event['start_time'] = serialized_event['start_time'].strftime("%Y-%m-%d %H:%M:%S")
                
            # Remove 'moved' flag as it's not needed in saved state
            if 'moved' in serialized_event:
                del serialized_event['moved']
                
            movements["mobility_events"][persona_name] = serialized_event
        
        # Fix: Fill in queue information
        # Facilities
        for facility_name, facility_data in self.maze.facilities_info.items():
            movements["queues"][facility_name] = {}
            
            if 'staying' in facility_data and facility_data['staying']:
                movements["queues"][facility_name]["staying"] = facility_data['staying'].copy()
                
            if 'waiting' in facility_data and facility_data['waiting']:
                movements["queues"][facility_name]["waiting"] = facility_data['waiting'].copy()
        
        # Nodes
        for node_name, node_data in self.maze.nodes_info.items():
            if 'waiting' in node_data and node_data['waiting']:
                movements["queues"][node_name] = {"waiting": node_data['waiting'].copy()}
        
        # Links
        for link_name, link_data in self.maze.links_info.items():
            queue_data = {}
            
            # Add driving queue if relevant
            if 'driving' in link_data and (link_data['driving'][0] or link_data['driving'][1]):
                # Combine both directions for simplicity
                queue_data["driving"] = link_data['driving'][0].copy() + link_data['driving'][1].copy()
                
            # Add walking queue if relevant
            if 'walking' in link_data and (link_data['walking'][0] or link_data['walking'][1]):
                queue_data["walking"] = link_data['walking'][0].copy() + link_data['walking'][1].copy()
                
            # Add riding queue if relevant
            if 'riding' in link_data and (link_data['riding'][0] or link_data['riding'][1]):
                queue_data["riding"] = link_data['riding'][0].copy() + link_data['riding'][1].copy()
                
            # Add waiting queue if relevant
            if 'waiting' in link_data and (link_data['waiting'][0] or link_data['waiting'][1]):
                queue_data["waiting"] = link_data['waiting'][0].copy() + link_data['waiting'][1].copy()
                
            # Only add this link to movements if it has any queues
            if queue_data:
                movements["queues"][link_name] = queue_data
            
        with open(movement_file, 'w') as f:
            json.dump(movements, f, indent=4)
        


    def start_server(self, int_counter): 
        """
        The main simulation function.
        
        Args:
            int_counter: Integer value for the number of steps left for us to take in this iteration. 
            
        Returns 
            None
            
        Note: Saves all relevant data to the designated memory directory
        """
        # prepare cache
        # meta
        curr_meta_f = f"{config.cache}/curr_meta.json"
        curr_meta = dict() 
        curr_meta["simulation_name"] = self.simulation_name
        curr_meta["curr_step"] = 0
        curr_meta["maze_name"] = self.maze.maze_name
        curr_meta["curr_time"] = self.curr_time.strftime("%Y-%m-%d %H:%M:%S")
        curr_meta["persona_names"] = list(self.population.keys())
        with open(curr_meta_f, "w") as f:
            json.dump(curr_meta, f, indent=4)
        # plans
        curr_plans_f = f"{config.cache}/curr_plans.json"
        curr_plans = dict()
        for persona_name in self.population.keys():
            curr_plans[persona_name] = None
        with open(curr_plans_f, "w") as f:
            json.dump(curr_plans, f, indent=4)
        # chats
        curr_messages_f = f"{config.cache}/curr_plans.json"
        curr_messages = dict()
        for persona_name in self.population.keys():
            curr_messages[persona_name] = None
        with open(curr_messages_f, "w") as f:
            json.dump(curr_messages, f, indent=4)
        
        # The main while loop of simulation. Iterate over simulation run steps.        
        while int_counter > 0: 
            # Done with this iteration if <int_counter> reaches 0. 
            print("-" * 80)
            print(f">>> Step: {self.step} | Current simulation time: {self.curr_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
            #====================================GATSIM Core=========================================================
            #======================Generate activity plan===========================
            """
            # Check all persona whether they need to a make new activity plan
            # does the event trigger new decision from agent at this step? if so, invoke persona.move() method
            # -  some events has to be finished as an integral part.
            # Say, driving half way of a road link, driver cannot make new movement decisions; once he arrived at the ending node, event 
            # manager should notify persona to make new movement decision;
            # -  Every event has max duration; say watching movie is 2 hours. Upon the ending of the event, new decision has to be made.
            # - Some events can be divided.
            # Say, persona can work at most for 10 hours. working state can trigger decision making every 2 hours; namely persona can decide whether to continue
            # working state for every 2 hours.
            
            The main cognition sequence happens in move():
                perceive -> retrieve -> plan -> reflect -> execute
            Each time the agent runs its decision-making logic (often in its move() method), 
            it can recalculate or overwrite that planned path if conditions change or if the agent decides on a new goal. For example:
             -	If the agent still wants to go to the same destination (and it hasn’t arrived yet), it just continues popping tiles from planned_path until it arrives.
             -	If the agent decides to change plans (maybe it sees something more urgent or is interrupted), it can reassign persona.st_mem.planned_path to a new path.
            Each step’s “pondering” (the agent’s logic) may well alter or reset planned_path based on the agent’s updated goals or the environment’s state.
            """
            for persona_name, persona in self.population.items():
                can_update_plan = self._check_if_persona_can_update_plan(persona_name)
                if can_update_plan:
                    #persona.plan_for_test(self.maze, self.population)
                    print()
                    pretty_print(f">>> {persona.st_mem.name} curr status: {persona.st_mem.curr_status} - now update plan", 1)
                    persona.plan(self.maze, self.population)
                    
            #=========================Update current activity=======================
            # Update persona activity when his or her current activity is done
            #  - planned_duration == None means leave up arrival, like dropping kid at School
            #  - departure_time + planned_duration == self.curr_time
            for persona_name, persona in self.population.items():
                departure_time = persona.st_mem.activity_departure_time
                planned_duration = persona.st_mem.activity_duration
                if persona.st_mem.curr_place == persona.st_mem.activity_facility \
                    and (planned_duration == None or departure_time + planned_duration == self.curr_time):
                    print()
                    pretty_print(f">>> {persona.st_mem.name} curr status: {persona.st_mem.curr_status} - now finished current activity; update the current activity", 1)
                    persona.update_activity(self.maze)
                          
            #=======================Simulate Mobility on Network=====================
            """
            Mobility simulation process:
            Now we describe the transport simulation process.
            Vehicle traversal over road link is queue-based. Road link has capacity; new vehicles can enter only when there is capacity left.
            Metro run according to transit schedule. Persona can only board the metro when the train arrives (maze.links_info[link]['arrival'][i] is true for direction i).
            Personas unable to drive or board the train need to wait at the link. Personas follow first-in, first-out (FIFO) rules to traverse links.
            All time will be represented by datetime object. 
            At the start of the simulation, initialize all personas to have mobility event "staying" at home_facility;
            The detailed simulation running process for each run step is as follows:
            
            Step 1: handling traversing events (link to node or continue to travel on link)
                 - Case 1: Move traveling personas from link to node when traversal has finished
                Check all mobility events of status "walking", "driving", "riding"
                    - for a driving persona, if his or her traversal time equal driving travel time (self.links_info[link]['travel time'][i]), move him or her to next_node by changing his or her mobility events from "driving" at link to "waiting" at node; also update queue lists;
                    - for a riding persona, if his or her traversal time equal riding travel time (self.links_info[link]['travel time'][i]), move him or her to next_node by changing his or her mobility events from "riding" at link to "waiting" at node; also update queue lists;
                    - for a walking persona, if his or her traversal time equal walking travel time (self.links_info[link]['travel time'][i] * config.walk_time_factor), move him or her to next_node by changing his or her mobility events from "walking" at link to "waiting" at nodes; also update queue lists;
                Update these persona mobility events to have "moved" being True;
                 
                 - Case 2: if traversal has not finished
                For personas whose traversing is not finished; make no changes to their mobility events; meaning that one more time step has passed as they continue to travel on the link;
                Update these persona mobility events to have "moved" being True;
            
            Step 2: handling departure events (facility to node) and finished events (node to facility)
                 - Case 1: Move personas from facility to node when departure times are due
                Check persona with "moved" being false that are at a facility (persona.st_mem.curr_place) and their planned activities departure time (persona.st_mem.activity_departure_time) is reached,
                move them from the facility to the facility's corresponding node by changing mobility event of status "staying" (or maybe "waiting") at facility to "waiting" at a node;
                Update facilities staying list (self.facilities_info[facility]['staying']); Update node waiting list (self.nodes_info[node]['waiting']);
                Update these persona mobility events to have "moved" being True;
                
                 - Case 2: Move personas who are at nodes and have finished their trips to facilities
                Check all personas waiting at a node with "moved" being false; 
                check if their planned trip is over (self.maze.facility2node(persona.st_mem.activity_facility) == self.mobility_events[persona_name]['place'])
                check their target facility capacity (maze.facilities_info[facility]['realtime capacity']) and number of people staying over there (maze.facilities_info[facility][staying]);
                then move them to facility to stay or wait at the facility, by changing their "waiting" at node mobility event to "staying" or "waiting" at facility mobility event;
                Update these persona mobility events to have "moved" being True;
            
            Step 3: handling link entering events (node to link)
                Step 3.1: Move personas waiting at a node to next_link
                Check all mobility events of status "waiting" at a node with "moved" being false;
                Pop (next_link, next_mode, next_node) from persona.st_mem.planned_path;
                Update mobility event by:
                 - Case 1: if this persona want to drive through this link, change this persona mobility event from "waiting" at node to "waiting" at the link (self.links_info[link]['waiting']);
                 - Case 2: if this persona want to riding through this link, change this persona mobility event from "waiting" at node to "waiting" at the link (self.links_info[link]['waiting']);
                 - Case 3: if this personas want to walk through the link, change this persona mobility event from waiting at the node to "walking" at link;
                
                Step 3.2: Move personas waiting at a link to traversing (waiting at link to traversing link)
                 - Case 1: Check all road links wait list: 
                 if the number of personas driving on the link (#driving) < link capacity (self.links_info[link]['realtime capacity]), 
                 move min(#waiting, link capacity - #driving) many personas from waiting at link to driving at link;
                 the rest personas need to continue "waiting" at link;
                 
                 - Case 2: Check all metro links wait list: 
                 if a metro arrives at a node, move min(metro link realtime capacity, #waiting) many personas with from "waiting" at link to "riding" at link;
                 the rest personas continue "waiting" at link;
                
                Step 3.3: Update these persona mobility event to have "moved" being True;
                 
            Step 4: Update network and facility states for personas to perceive:
                 - Update road link "wait time" attribute;
                 - Update facility "wait time" and "crowdedness" attributes;
                 - Reset all persona moved to be False for next run step.
            
            Notes:
             - Setting these personas "moved" flag to true means that this persona has already moved at this run step; 
             - for all movements, personas follow FIFO rule;
             - remember to update attributes "start_time" when the mobility events are under change;
             - mobility event's 'next_node' is not None only when a persona pop his or her planned path to enter a link;
             - link wait time experience, path experience should be updated to memory
            
            Related variables:
             - self.mobility_events[persona_name]['moved']
                # namely the "persona moved" variable;
                # bool; true if this persona has already moved at this run step;
             - persona.st_mem.curr_place  
                # Persona current location (link / node / facility name)
             - persona.st_mem.planned_path  
                # Persona movement plan, a list of (next_link, next_mode, next_node) tuples; 
                # next_mode: "walk" / "drive" / "ride"
                # this list is empty if user is not planning to move
                # persona.st_mem.planned_path[0] is next move that simulator cares about
             - persona.st_mem.activity_facility  
                # Persona planned activity location (facility name)
             - persona.st_mem.activity_departure_time
                # Persona planned activity departure time, a datetime object
             - maze.links_info[link]['realtime capacity'][i]  
                # link's realtime capacity for direction i (i = 0, 1)
             - maze.links_info[link]['driving'][i]  
                # number of moving personas on a road link with direction i (i = 0, 1)
                # it's a list of persona names; 
             - maze.links_info[link]['riding'][i]
                # number of moving personas on a metro link with direction i (i = 0, 1)
                # it's a list of persona names; 
             - maze.links_info[link]['waiting'][i] 
                # if the link is road link, it means the number of personas waiting to drive through the road link for direction i (i = 0, 1)
                # if the link is metro link, it means the number of personas waiting to board the metro link for direction i (i = 0, 1)
                # a list of persona names
             - maze.links_info[link]['arrival'][i]
                # link must be metro link
                # True if there is a metro waiting at this link for direction i at this run step
             - maze.nodes_info[node]['waiting']  
                # number of personas waiting at a node to enter next link or facility
             - maze.facilities_info[facility]['staying']
                # number of personas staying in the facility, engaged in their planned activities;
             - maze.facilities_info[facility]['waiting']
                # number of personas waiting at the facility
             - maze.update(curr_time)
                # method to update the maze state 
            """
            # Step 0. Update the maze state for the current time
            # this is for loading NetworkEvents, like car crash, transit schedule, which may affects capacity of links
            self.maze.update(self.curr_time)
            # Step 1: Handling traversing events (link to node or continue to travel on link)
            self._handle_traversing_events()
            # Step 2: Handling departure events (facility to node) and finished events (node to facility)
            self._handle_departure_events()
            # Step 3: Handling finished events (node to facility waiting, facility waiting to facility staying)
            self._handle_finished_events()
            # Step 4: Handling link entering events (node to link)
            self._handle_link_entering_events()
            # Step 5: Update network and facility states for personas to perceive
            self._update_network_state()
            
            #=====================Reflect Daily Experiences========================
            # check whether it's end of the day (for daily reflection)
            end_of_day = False
            next_time = self.curr_time + timedelta(minutes=config.minutes_per_step)
            if self.curr_time.day != next_time.day:
                end_of_day = True
            # Check if it's a new day or if it's the end of the day
            for persona_name, persona in self.population.items():
                # If it's the end of the day, reflect on the day.
                if end_of_day:
                    # reflect on daily experiences
                    # saved to self.st_mem.daily_reflections
                    # daily_reflection at end of day and original plan (reflection) of last morning will be combined to produce original plan for next day.
                    print()
                    pretty_print(f">>> {persona.st_mem.name} curr status: {persona.st_mem.curr_status} - now reflecting on daily experiences", 1)
                    persona.daily_reflection(self.maze)  
            
            #====================Save and Advance Simulation======================
            # save meta data, memory and movements
            self.save()
            
            # also update cache

            # Advance simulation step/time
            # After this cycle, the world takes one step forward, and the 
            # current time moves by <minutes_per_step> amount. 
            self.step += 1
            int_counter -= 1
            self.curr_time += timedelta(minutes=self.minutes_per_step)  # backend time updated
            for persona in self.population.values():
                persona.st_mem.curr_time = self.curr_time  # persona st_mem time updated
                persona.lt_mem.curr_time = self.curr_time  # persona lt_mem time updated
            # Sleep so we don't burn our machines. 
            time.sleep(self.server_sleep)
            
            # clean cached chats
            cache_chat_f = f"{config.cache}/curr_chats.json"
            if os.path.exists(cache_chat_f):
                os.remove(cache_chat_f)
            
            # save cache meta
            curr_meta_f = f"{config.cache}/curr_meta.json"
            curr_meta = dict() 
            curr_meta["simulation_name"] = self.simulation_name
            curr_meta["curr_step"] = self.step
            curr_meta["maze_name"] = self.maze.maze_name
            curr_meta["curr_time"] = self.curr_time.strftime("%Y-%m-%d %H:%M:%S")
            curr_meta["persona_names"] = list(self.population.keys())
            with open(curr_meta_f, "w") as f:
                json.dump(curr_meta, f, indent=4)
            #====================================GATSIM Core End======================================================


    def _handle_traversing_events(self):
        """
        Step 1: Handle traversing events (link to node or continue to travel on link)
        - Move personas from link to node when traversal is finished
        - Otherwise, update traversal time for personas still on links
        """
        # Iterate through all mobility events
        for persona_name, event in self.mobility_events.items():
            # Skip personas that have already moved in this step or are not traversing links
            if event['moved'] or event['status'] not in ["driving", "riding", "walking"]:
                continue
            
            # Get the current link
            link_name = event['place']
            if link_name not in self.maze.links_info:
                continue  # Skip if link doesn't exist
                
            # Determine which direction the persona is traveling (0 or 1)
            endpoints = self.maze.links_info[link_name]['endpoints']
            next_node = event['next_node']
            direction = 1 if next_node == endpoints[0] else 0
            
            # Calculate time spent on link
            time_spent = int((self.curr_time - event['start_time']).total_seconds() / 60)  # in minutes
            
            # Get applicable travel time based on mode
            if event['status'] == "walking":
                travel_time = self.maze.links_info[link_name]['travel time'] * config.walk_time_factor
            else:  # driving or riding
                travel_time = self.maze.links_info[link_name]['travel time']
            
            # Check if traversal is complete
            if time_spent >= travel_time:
                # Move persona from link to node
                
                # 1. Remove from link queue
                if event['status'] == "driving" and persona_name in self.maze.links_info[link_name]['driving'][direction]:
                    self.maze.links_info[link_name]['driving'][direction].remove(persona_name)
                elif event['status'] == "riding" and persona_name in self.maze.links_info[link_name]['riding'][direction]:
                    self.maze.links_info[link_name]['riding'][direction].remove(persona_name)
                elif event['status'] == "walking" and persona_name in self.maze.links_info[link_name]['walking'][direction]:
                    self.maze.links_info[link_name]['walking'][direction].remove(persona_name)
                
                # 2. Add to node waiting queue
                if next_node not in self.maze.nodes_info:
                    print(f"Warning: Next node {next_node} not found for {persona_name}")
                    continue
                    
                self.maze.nodes_info[next_node]['waiting'].append(persona_name)
                
                # 3. Update mobility event
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': next_node,
                    'next_node': None,
                    'status': "waiting",
                    'start_time': self.curr_time,
                    'description': event['description'],  # Keep the same activity description
                    'moved': True
                }
                # Update coordinates of the event
                coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                self.mobility_events[persona_name]['coord'] = coord
                
                # update cache file for frontend visualization (movements.json)
                json_path = 'gatsim/cache/curr_movements.json'
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data['mobility_events'][persona_name] = {
                    'name': event['name'],
                    'place': next_node,
                    'next_node': None,
                    'status': "waiting",
                    'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'description': event['description'],  # Keep the same activity description
                    'moved': True,
                    'coord': coord
                }
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
        
                
                # 4. Update persona current place
                self.population[persona_name].st_mem.curr_place = next_node

            else:
                # Persona continues traversing the link
                self.mobility_events[persona_name]['moved'] = True
                
                # update cache file for frontend visualization (movements.json)
                # Use interpolation to get the coordinates
                # This is only for visualization purposes
                coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                json_path = 'gatsim/cache/curr_movements.json'
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data['mobility_events'][persona_name] = copy.deepcopy(self.mobility_events[persona_name])
                data['mobility_events'][persona_name]['start_time'] = data['mobility_events'][persona_name]['start_time'].strftime("%Y-%m-%d %H:%M:%S")
                data['mobility_events'][persona_name]['coord'] = coord
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)


    def _handle_departure_events(self):
        """
        Step 2: Handle departure events (facility to node)
        - Move personas from facility to node when departure times are due
        """
        # Handle departure events (facility to node)
        for persona_name, event in self.mobility_events.items():
            persona = self.population[persona_name]
            
            # Skip personas that have already moved in this step or not staying at a facility
            if event['moved'] or event['status'] != "staying":
                continue
                
            # Check if persona is now in a facility
            facility_name = event['place']
            if facility_name not in self.maze.facilities_info:
                continue
                
            # Check if departure time has arrived
            if hasattr(persona.st_mem, "activity_departure_time") and \
            self.curr_time == persona.st_mem.activity_departure_time:
                # add trip variables
                # why they are needed?
                # persona.st_mem record the current activity information
                # we also need to record last activity facility (trip origin) etc. information
                persona.trip_start_facility = persona.st_mem.curr_place
                persona.trip_trajectory = []  # record persona travel trajectory; append as persona travel on the network.
                
                # if the next activity happens in the same facility, we don't need to move the persona
                if persona.st_mem.curr_place == persona.st_mem.activity_facility:
                    continue
                
                # Get the node corresponding to this facility
                node_name = self.maze.facility2node.get(facility_name)
                if not node_name:
                    pretty_print(f"Warning: No node found for facility {facility_name}", 1)
                    continue
                    
                # 1. Remove from facility staying list
                if persona_name in self.maze.facilities_info[facility_name]['staying']:
                    self.maze.facilities_info[facility_name]['staying'].remove(persona_name)
                    
                # 2. Add to node waiting list
                self.maze.nodes_info[node_name]['waiting'].append(persona_name)
                
                # 3. Update mobility event and persona state
                persona.st_mem.curr_place = node_name
                persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.trip_start_facility} to {persona.st_mem.activity_facility}; planned path: {persona.st_mem.planned_path} trajectory: {persona.trip_trajectory}; currently at node {node_name}"
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': node_name,
                    'next_node': None,
                    'status': "waiting",
                    'start_time': self.curr_time,
                    'description': f"going to {persona.st_mem.activity_facility}" if hasattr(persona.st_mem, "activity_facility") else "leaving",
                    'moved': True
                }
                # Update coordinates of the event
                coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                self.mobility_events[persona_name]['coord'] = coord
                pretty_print(f"Departure event: {persona.st_mem.curr_status}", 1)
                
                # update cache file for frontend visualization (movements.json)
                json_path = 'gatsim/cache/curr_movements.json'
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data['mobility_events'][persona_name] = {
                    'name': event['name'],
                    'place': node_name,
                    'next_node': None,
                    'status': "waiting",
                    'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'description': f"going to {persona.st_mem.activity_facility}" if hasattr(persona.st_mem, "activity_facility") else "leaving",
                    'moved': True,
                    'coord': coord
                }
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                
            else:
                # departure time not due yet
                persona.st_mem.curr_place = facility_name
                persona.st_mem.curr_status = f"Staying at facility {facility_name}"
    
    
    def _handle_finished_events(self):
        """
        Step 3: Handle finished events (node to facility waiting, facility waiting to facility staying)
        - 3.1) Move personas from facility to node when departure times are due
        - 3.2) Move personas from node to facility when their trip is over
        """
        
        # Step 3.1: Handle finished events (node to facility waiting)
        for persona_name, event in self.mobility_events.items():
            persona = self.population[persona_name]
            
            # Skip personas that have already moved in this step or not waiting at a node
            if event['moved'] or event['status'] != "waiting":
                continue
                
            # Check if this is a node
            node_name = event['place']
            if node_name not in self.maze.nodes_info:
                continue
                
            # Check if persona has reached their target facility's node
            target_facility = getattr(persona.st_mem, "activity_facility", None)
            if not target_facility:
                continue
                
            target_node = self.maze.facility2node.get(target_facility)
            if target_node != node_name:
                continue
                
            # Persona has reached destination node, move to facility
            #===Add trip experience to memory===
            type = "event"
            created = self.curr_time
            trip_time = int((self.curr_time - persona.st_mem.activity_departure_time).total_seconds() / 60)
            start_time_str = persona.st_mem.activity_departure_time.strftime("%a %Y-%m-%d %H:%M")
            content = f"{persona_name} travels from {persona.trip_start_facility} to {persona.st_mem.activity_facility} by travel mode {persona.st_mem.travel_mode}; start time is {start_time_str}; duration is {trip_time} minutes"
            keywords = [f"{persona.trip_start_facility} to {persona.st_mem.activity_facility}", f"{persona.st_mem.travel_mode}"]
            spatial_scope = f"{persona.trip_start_facility}, {persona.st_mem.activity_facility}"
            for seg in persona.trip_trajectory:
                road_name = seg[0].split('_')[0] + seg[0].split('_')[1]
                spatial_scope += ', ' + road_name
            time_scope = [persona.st_mem.activity_departure_time.time(), self.curr_time.time()]
            importance = generate_importance_score(persona, self.maze, "event", content)
            node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
            persona.lt_mem.add_concept_node(node)
            # re-initialize trip variables
            persona.trip_start_facility = None
            persona.trip_trajectory = None
            
            # 1. Remove from node waiting list
            if persona_name in self.maze.nodes_info[node_name]['waiting']:
                self.maze.nodes_info[node_name]['waiting'].remove(persona_name)
            
            # persona join wait queue at facility
            self.maze.facilities_info[target_facility]['waiting'].append(persona_name)
            new_status = "waiting"
            
            # 3. Update mobility event and persona state
            persona.st_mem.curr_place = target_facility
            persona.st_mem.curr_status = f"Just finished the trip from {persona.trip_start_facility} to {persona.st_mem.activity_facility}; waiting at {persona.st_mem.activity_facility} now"
            # Note: add trip time to the status
            self.mobility_events[persona_name] = {
                'name': event['name'],
                'place': target_facility,
                'next_node': None,
                'status': new_status,
                'start_time': self.curr_time,
                'description': f"{new_status} at {target_facility}",
                'moved': False  # Set to False so this persona can be moved in step 3.2
            }
            # Update coordinates of the event
            coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
            self.mobility_events[persona_name]['coord'] = coord
            
            # update cache file for frontend visualization (movements.json)
            json_path = 'gatsim/cache/curr_movements.json'
            with open(json_path, 'r') as f:
                data = json.load(f)
            data['mobility_events'][persona_name] = {
                'name': event['name'],
                'place': target_facility,
                'next_node': None,
                'status': new_status,
                'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                'description': f"{new_status} at {target_facility}",
                'moved': False,  # Set to False so this persona can be moved in step 3.2
                'coord': coord
            }
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            # 4. Reset planned path since destination is reached
            persona.st_mem.planned_path = []
            
        # step 3.2: Handle finished events (facility waiting to facility staying)
        for facility_name in self.maze.facilities_info:
            current_occupancy = len(self.maze.facilities_info[facility_name]['staying'])
            available_capacity = self.maze.facilities_info[facility_name]['realtime capacity'] - current_occupancy
            
            # Get the number of personas waiting at the facility
            waiting_personas = self.maze.facilities_info[facility_name]['waiting']
                        
            # Make a copy of the waiting personas list for iteration
            # as we'll be modifying the original list during the loop
            waiting_personas_copy = waiting_personas.copy()
            # Sort waiting personas by arrival time (FIFO)
            # We need to sort the copy, not the original
            waiting_personas_copy.sort(key=lambda p: self.mobility_events[p]['start_time'])
            
            # Move as many personas as capacity allows
            personas_to_move = min(len(waiting_personas_copy), available_capacity)
            
            # Track which personas were moved to driving status
            moved_personas = []
            
            for i in range(personas_to_move):
                if i >= len(waiting_personas_copy):
                    break
                    
                persona_name = waiting_personas_copy[i]
                persona = self.population[persona_name]  # remember to update persona object
                # Skip if persona has already moved
                if self.mobility_events[persona_name]['moved']:
                    continue
                    
                # Add to list of personas to move
                moved_personas.append(persona_name)
            
                wait_time = int((self.curr_time - self.mobility_events[persona_name]['start_time']).total_seconds() / 60)
                # Update mobility event and persona state
                persona.st_mem.curr_place = facility_name
                persona.st_mem.curr_status = f"{persona_name} Currently staying at facility {facility_name} engaged in the target activity after waiting for {wait_time} minutes at the facility"
                # Note: add facility wait time to the status
                self.mobility_events[persona_name] = {
                    'name': self.mobility_events[persona_name]['name'],
                    'place': facility_name,
                    'next_node': None,
                    'status': "staying",
                    'start_time': self.curr_time,
                    'description': f"Staying at {facility_name}",
                    'moved': True
                }
                # Update coordinates of the event
                coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                self.mobility_events[persona_name]['coord'] = coord
                pretty_print(f"Activity finishing event: {persona.st_mem.curr_status}", 1)
                
                # update cache file for frontend visualization (movements.json)
                json_path = 'gatsim/cache/curr_movements.json'
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data['mobility_events'][persona_name] = {
                    'name': self.mobility_events[persona_name]['name'],
                    'place': facility_name,
                    'next_node': None,
                    'status': "staying",
                    'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'description': f"Staying at {facility_name}",
                    'moved': True,
                    'coord': coord
                }
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                        
            # Now update the actual lists
            for persona_name in moved_personas:
                # Remove from waiting list
                if persona_name in self.maze.facilities_info[facility_name]['waiting']:
                    self.maze.facilities_info[facility_name]['waiting'].remove(persona_name)
                    
                    # Add to facility staying list
                    self.maze.facilities_info[facility_name]['staying'].append(persona_name)
                
            # Mark remaining waiting personas as moved (they've been processed)
            for persona_name in self.maze.facilities_info[facility_name]['staying']:
                if not self.mobility_events[persona_name]['moved']:
                    self.mobility_events[persona_name]['moved'] = True
            

    def _handle_link_entering_events(self):
        """
        Step 4: Handle link entering events (node to link)
        
        - Move personas from node to link waiting queue (Step 3.1)
        - Move personas from link waiting queue to traversing the link (Step 3.2)
        """
        # Step 4.1: Move personas waiting at a node to the next link's waiting queue
        for persona_name, event in self.mobility_events.items():
            persona = self.population[persona_name]
            
            # Skip personas that have already moved in this step or not waiting at a node
            if event['moved'] or event['status'] != "waiting":
                continue
                
            # Check if this is a node
            node_name = event['place']
            if node_name not in self.maze.nodes_info:
                continue
                
            # Check if persona has a planned path
            if not hasattr(persona.st_mem, "planned_path") or not persona.st_mem.planned_path:
                continue
                
            #====how is how simulation core knows where persona wants to to====
            # Get the next move from the planned path
            next_move = persona.st_mem.planned_path[0]  # Don't pop yet, we'll do it when successfully entering the link
            # Note: next_move will be popped out afterwards
            #==================================================================
            
            if len(next_move) < 3:
                pretty_print(f"Warning: Invalid next_move format for {persona_name}: {next_move}", 1)
                continue
                
            next_link, next_mode, next_node = next_move
            
            # Verify the next link exists
            if next_link not in self.maze.links_info:
                pretty_print(f"Warning: Link {next_link} not found in maze for {persona_name}", 1)
                continue
                
            # Determine the direction for this link
            endpoints = self.maze.links_info[next_link]['endpoints']
            
            # Direction is 0 if going from endpoints[0] to endpoints[1], otherwise 1
            direction = 0 if (node_name == endpoints[0] and next_node == endpoints[1]) else 1
            
            # Based on the next_mode, update the mobility event and queue lists
            if next_mode == "drive":
                if self.maze.links_info[next_link]['type'] != 'road':
                    pretty_print(f"Warning: Cannot drive on non-road link {next_link}", 1)
                    continue
                    
                # Remove from node waiting queue
                if persona_name in self.maze.nodes_info[node_name]['waiting']:
                    self.maze.nodes_info[node_name]['waiting'].remove(persona_name)
                    
                # Add to link waiting queue
                self.maze.links_info[next_link]['waiting'][direction].append(persona_name)
                
                # Update mobility event and persona state
                persona.st_mem.curr_place = next_link
                persona.st_mem.curr_status = f"On the trip from {persona.trip_start_facility} to {persona.st_mem.activity_facility}; path: {persona.trip_trajectory}; currently waiting at link {next_link}"
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "waiting",  # Will be changed to "driving" in Step 3.2 if capacity allows
                    'start_time': self.curr_time,
                    'description': event['description'],
                    'moved': False  # Set to False so this persona can be moved in step 3.2
                }
                # Update coordinates of the event
                coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                self.mobility_events[persona_name]['coord'] = coord
                
                # update cache file for frontend visualization (movements.json)
                json_path = 'gatsim/cache/curr_movements.json'
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data['mobility_events'][persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "waiting",  # Will be changed to "driving" in Step 3.2 if capacity allows
                    'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'description': event['description'],
                    'moved': False,  # Set to False so this persona can be moved in step 3.2
                    'coord': coord
                }
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Pop the next move from the planned path
                persona.st_mem.planned_path.pop(0)
                
            elif next_mode == "ride":
                if self.maze.links_info[next_link]['type'] != 'metro':
                    pretty_print(f"Warning: Cannot ride on non-metro link {next_link}", 1)
                    continue
                    
                # Remove from node waiting queue
                if persona_name in self.maze.nodes_info[node_name]['waiting']:
                    self.maze.nodes_info[node_name]['waiting'].remove(persona_name)
                    
                # Add to link waiting queue
                self.maze.links_info[next_link]['waiting'][direction].append(persona_name)
                
                # Update mobility event and persona state
                persona.st_mem.curr_place = next_link
                persona.st_mem.curr_status = f"On the trip from {persona.trip_start_facility} to {persona.st_mem.activity_facility}; path: {persona.trip_trajectory}; currently waiting at link {next_link}"
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "waiting",  # Will be changed to "riding" in Step 3.2 if metro arrives
                    'start_time': self.curr_time,
                    'description': event['description'],
                    'moved': False  # Set to False so this persona can be moved in step 3.2
                }
                # Update coordinates of the event
                coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                self.mobility_events[persona_name]['coord'] = coord
                
                # update cache file for frontend visualization (movements.json)
                json_path = 'gatsim/cache/curr_movements.json'
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data['mobility_events'][persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "waiting",  # Will be changed to "riding" in Step 3.2 if metro arrives
                    'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'description': event['description'],
                    'moved': False,  # Set to False so this persona can be moved in step 3.2
                    'coord': coord
                }
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Pop the next move from the planned path
                persona.st_mem.planned_path.pop(0)
                
            elif next_mode == "walk":
                # For walking, we can directly move to the link (no capacity constraints)
                
                # Remove from node waiting queue
                if persona_name in self.maze.nodes_info[node_name]['waiting']:
                    self.maze.nodes_info[node_name]['waiting'].remove(persona_name)
                    
                # Add directly to link walking queue (no waiting)
                self.maze.links_info[next_link]['walking'][direction].append(persona_name)
                
                # Update mobility event and persona state
                persona.st_mem.curr_place = next_link
                persona.st_mem.curr_status = f"On the trip from {persona.trip_start_facility} to {persona.st_mem.activity_facility}; path: {persona.trip_trajectory}; currently walking on link {next_link}"
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "walking",
                    'start_time': self.curr_time,
                    'description': event['description'],
                    'moved': True  # Already in walking state, so mark as moved
                }
                # Update coordinates of the event
                coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                self.mobility_events[persona_name]['coord'] = coord
                
                # update cache file for frontend visualization (movements.json)
                json_path = 'gatsim/cache/curr_movements.json'
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data['mobility_events'][persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "walking",
                    'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'description': event['description'],
                    'moved': True,  # Already in walking state, so mark as moved
                    'coord': coord
                }
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Pop the next move from the planned path
                persona.st_mem.planned_path.pop(0)
                
        # Step 4.2: Move personas from link waiting queue to traversing the link
        for link_name in self.maze.links_info:
            # Handle road links first
            if self.maze.links_info[link_name]['type'] == 'road':
                for direction in [0, 1]:
                    # Get the number of personas waiting and driving
                    waiting_personas = self.maze.links_info[link_name]['waiting'][direction]
                    
                    # Make a copy of the waiting personas list for iteration
                    # as we'll be modifying the original list during the loop
                    waiting_personas_copy = waiting_personas.copy()
                    
                    # Calculate how many personas can start driving
                    capacity = self.maze.links_info[link_name]['realtime capacity'][direction]
                    available_capacity = capacity - len(self.maze.links_info[link_name]['driving'][direction])
                    
                    # Sort waiting personas by arrival time (FIFO)
                    # We need to sort the copy, not the original
                    waiting_personas_copy.sort(key=lambda p: self.mobility_events[p]['start_time'])
                    
                    # Move as many personas as capacity allows
                    personas_to_move = min(len(waiting_personas_copy), available_capacity)
                    
                    # Track which personas were moved to driving status
                    moved_personas = []
                    
                    for i in range(personas_to_move):
                        if i >= len(waiting_personas_copy):
                            break
                            
                        persona_name = waiting_personas_copy[i]
                        persona = self.population[persona_name]  # remember to update persona obj
                        
                        # Skip if persona has already moved
                        if self.mobility_events[persona_name]['moved']:
                            continue
                            
                        # Add to list of personas to move
                        moved_personas.append(persona_name)
                        
                        #===Add trip experience to memory===
                        type = 'event'
                        created = self.curr_time
                        wait_time = int((self.curr_time - self.mobility_events[persona_name]['start_time']).total_seconds() / 60)
                        start_time_str = self.mobility_events[persona_name]['start_time'].strftime("%a %Y-%m-%d %H:%M")
                        content = f"{persona_name} waits at {link_name}; start time is {start_time_str}; duration is {wait_time} minutes"
                        keywords = ["wait", link_name]
                        spatial_scope = link_name
                        time_scope = [self.mobility_events[persona_name]['start_time'].time(), self.curr_time.time()]
                        importance = generate_importance_score(persona, self.maze, "event", content)
                        node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
                        persona.lt_mem.add_concept_node(node)
                        
                        # Update mobility event and persona state
                        persona.st_mem.curr_place = link_name
                        persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.trip_start_facility} to {persona.st_mem.activity_facility}; path: {persona.trip_trajectory}; currently traveling on link {link_name} after waiting for {wait_time} minutes"
                        # Note to add link wait time to status
                        self.mobility_events[persona_name] = {
                            'name': self.mobility_events[persona_name]['name'],
                            'place': link_name,
                            'next_node': self.mobility_events[persona_name]['next_node'],
                            'status': "driving",
                            'start_time': self.curr_time,
                            'description': self.mobility_events[persona_name]['description'],
                            'moved': True
                        }
                        # Update coordinates of the event
                        coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                        self.mobility_events[persona_name]['coord'] = coord
                        
                        # update cache file for frontend visualization (movements.json)
                        json_path = 'gatsim/cache/curr_movements.json'
                        with open(json_path, 'r') as f:
                            data = json.load(f)
                        data['mobility_events'][persona_name] = {
                            'name': self.mobility_events[persona_name]['name'],
                            'place': link_name,
                            'next_node': self.mobility_events[persona_name]['next_node'],
                            'status': "driving",
                            'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                            'description': self.mobility_events[persona_name]['description'],
                            'moved': True,
                            'coord': coord
                        }
                        with open(json_path, 'w') as f:
                            json.dump(data, f, indent=4)
                    
                    # Now update the actual lists
                    for persona_name in moved_personas:
                        # Remove from waiting list
                        if persona_name in self.maze.links_info[link_name]['waiting'][direction]:
                            self.maze.links_info[link_name]['waiting'][direction].remove(persona_name)
                        
                        # Add to driving list
                        self.maze.links_info[link_name]['driving'][direction].append(persona_name)
                    
                    # Mark remaining waiting personas as moved (they've been processed)
                    for persona_name in self.maze.links_info[link_name]['waiting'][direction]:
                        if not self.mobility_events[persona_name]['moved']:
                            self.mobility_events[persona_name]['moved'] = True
            
            # Handle metro links
            elif self.maze.links_info[link_name]['type'] == 'metro':
                for direction in [0, 1]:
                    # Check if a train has arrived at this station
                    if self.maze.links_info[link_name]['arrival'][direction]:
                        # Get the number of personas waiting and riding
                        waiting_personas = self.maze.links_info[link_name]['waiting'][direction]
                        
                        # Make a copy of the waiting personas list for iteration
                        waiting_personas_copy = waiting_personas.copy()
                        
                        # Calculate how many personas can board
                        capacity = self.maze.links_info[link_name]['realtime capacity'][direction]
                        available_capacity = capacity - len(self.maze.links_info[link_name]['riding'][direction])
                        
                        # Sort waiting personas by arrival time (FIFO)
                        waiting_personas_copy.sort(key=lambda p: self.mobility_events[p]['start_time'])
                        
                        # Move as many personas as capacity allows
                        personas_to_move = min(len(waiting_personas_copy), available_capacity)
                        
                        # Track which personas were moved to riding status
                        moved_personas = []
                        
                        for i in range(personas_to_move):
                            if i >= len(waiting_personas_copy):
                                break
                                
                            persona_name = waiting_personas_copy[i]
                            persona = self.population[persona_name]  # remember to update persona obj
                            
                            # Skip if persona has already moved
                            if self.mobility_events[persona_name]['moved']:
                                continue
                                
                            # Add to list of personas to move
                            moved_personas.append(persona_name)
                            
                            #===Add trip experience to memory===
                            type = 'event'
                            created = self.curr_time
                            wait_time = int((self.curr_time - self.mobility_events[persona_name]['start_time']).total_seconds() / 60)
                            start_time_str = self.mobility_events[persona_name]['start_time'].strftime("%a %Y-%m-%d %H:%M")
                            content = f"{persona_name} waits at {link_name}; start time is {start_time_str}; duration is {wait_time} minutes"
                            keywords = ["wait", link_name]
                            spatial_scope = link_name
                            time_scope = [self.mobility_events[persona_name]['start_time'].time(), self.curr_time.time()]
                            importance = generate_importance_score(persona, self.maze, "event", content)
                            node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
                            persona.lt_mem.add_concept_node(node)
                                                    
                            # Update mobility event and persona state
                            persona.st_mem.curr_place = link_name
                            persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.trip_start_facility} to {persona.st_mem.activity_facility}; path: {persona.trip_trajectory}; currently waiting at link {link_name}"
                            self.mobility_events[persona_name] = {
                                'name': self.mobility_events[persona_name]['name'],
                                'place': link_name,
                                'next_node': self.mobility_events[persona_name]['next_node'],
                                'status': "riding",
                                'start_time': self.curr_time,
                                'description': self.mobility_events[persona_name]['description'],
                                'moved': True
                            }
                            # Update coordinates of the event
                            coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
                            self.mobility_events[persona_name]['coord'] = coord
                            
                            # update cache file for frontend visualization (movements.json)
                            json_path = 'gatsim/cache/curr_movements.json'
                            with open(json_path, 'r') as f:
                                data = json.load(f)
                            data['mobility_events'][persona_name] = {
                                'name': self.mobility_events[persona_name]['name'],
                                'place': link_name,
                                'next_node': self.mobility_events[persona_name]['next_node'],
                                'status': "riding",
                                'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                                'description': self.mobility_events[persona_name]['description'],
                                'moved': True,
                                'coord': coord
                            }
                            with open(json_path, 'w') as f:
                                json.dump(data, f, indent=4)
                        
                        # Now update the actual lists
                        for persona_name in moved_personas:
                            # Remove from waiting list
                            if persona_name in self.maze.links_info[link_name]['waiting'][direction]:
                                self.maze.links_info[link_name]['waiting'][direction].remove(persona_name)
                            
                            # Add to riding list
                            self.maze.links_info[link_name]['riding'][direction].append(persona_name)
                        
                        # Mark remaining waiting personas as moved (they've been processed)
                        for persona_name in self.maze.links_info[link_name]['waiting'][direction]:
                            if not self.mobility_events[persona_name]['moved']:
                                self.mobility_events[persona_name]['moved'] = True


    def _update_network_state(self):
        """
        Step 4: Update network and facility states for personas to perceive
        
        - Update road link "wait time" attribute based on congestion
        - Update facility "wait time" and "crowdedness" attributes
        - Reset all persona moved flags for next run step
        """
        # Update road link wait times based on congestion
        for link_name in self.maze.links_info:
            if self.maze.links_info[link_name]["type"] == "road":
                for direction in [0, 1]:
                    # Calculate congestion level
                    link_capacity = self.maze.links_info[link_name]["realtime capacity"][direction]
                    current_vehicles = len(self.maze.links_info[link_name]["driving"][direction])
                    
                    # Simple congestion model: wait time increases as vehicle count approaches capacity
                    if link_capacity > 0:
                        congestion_ratio = current_vehicles / link_capacity
                        # Wait time formula: 0 when empty, increases exponentially as ratio approaches 1
                        if congestion_ratio < 0.7:
                            wait_time = 0
                        elif congestion_ratio < 0.9:
                            wait_time = 2 * (congestion_ratio - 0.7) / 0.2  # 0-2 minutes
                        else:
                            wait_time = 2 + 8 * (congestion_ratio - 0.9) / 0.1  # 2-10 minutes
                        
                        # Update wait time
                        self.maze.links_info[link_name]["wait time"][direction] = round(wait_time, 1)
        
        # Update facility wait times and crowdedness
        for facility_name in self.maze.facilities_info:
            # Calculate occupancy
            capacity = self.maze.facilities_info[facility_name]["realtime capacity"]
            current_occupancy = len(self.maze.facilities_info[facility_name]["staying"]) + len(self.maze.facilities_info[facility_name]["waiting"])
            
            # Calculate wait time based on occupancy ratio
            if capacity > 0:
                occupancy_ratio = current_occupancy / capacity
                if occupancy_ratio < 0.8:
                    wait_time = 0
                else:
                    wait_time = 5 * (occupancy_ratio - 0.8) / 0.2  # 0-5 minutes
                
                # Update wait time
                self.maze.facilities_info[facility_name]["wait time"] = round(wait_time, 1)
        
        # Reset all persona moved flags for next run step
        for persona_name in self.population:
            self.mobility_events[persona_name]['moved'] = False
        
        

    def _check_if_persona_can_update_plan(self, persona_name):
        """
        Check if a persona should make a new decision based on their current state
        A persona can update their activity plan (or just path) under the following conditions:
        1. if it's new day, make the "original plan"
        2. If the persona is traveling, he or she can only update plan when waiting at a node (which last for 1 time step);
        3. When an activity finished and another activity is about to departure , persona can change mind before departure
        4. If the persona is at facility, he or she can update plan for every (reflect_every) minutes, or when departure time is now;
        
        Args:
            persona_name (str): Name of the persona
            
        Returns:
            (bool): True if persona should make a new decision, False otherwise
        """
        # check whether it's new day
        new_day = False
        last_time = self.curr_time - timedelta(minutes=config.minutes_per_step)
        if self.curr_time.day != last_time.day:
            new_day = True
            
        if new_day:
            return True
        
        event = self.mobility_events[persona_name]  # current persona mobility event
        persona = self.population[persona_name]
        departure_time = persona.st_mem.activity_departure_time
        duration = self.curr_time - departure_time
        planned_duration = persona.st_mem.activity_duration
        
        # Check current event type and location
        if event['status'] == "waiting" and event['place'] in self.maze.nodes_info:
            # 1. If waiting at a node, persona can update plan
            return True
            
        elif event['status'] == "staying" and event['place'] in self.maze.facilities_info:
            # 2. If the current activity just finished, and departure time for next activity is due
            if event['place'] == persona.st_mem.activity_facility \
                and (planned_duration == None or duration == planned_duration):
                return True
                
            # 3. Check if activity can be interrupted (based on reflect_every parameter)
            reflect_every = persona.st_mem.reflect_every  # timedelta
            if reflect_every != None:
                # reflect_every == None means this activity cannot been interrupted
                duration_int = int(duration.total_seconds() / 60)  # in minutes
                reflect_every_int = int(reflect_every.total_seconds() / 60)
                # If enough time has passed, allow decision
                if duration_int % reflect_every_int == 0:
                    return True

        # By default, don't make a new decision
        return False
        



    def open_server(self): 
        """
        Open up an interactive terminal prompt that lets you run the simulation 
        step by step and probe agent state. 

        Args: 
            None
            
        Returns
            None
        """
        # <simulation_folder> points to the current simulation folder.
        simulation_folder = f"{config.persona_storage}/{self.simulation_name}"

        while True: 
            sim_command = input("\nEnter option: (e.g. 'run 1 day', 'run 8 hours'; default: 'run 1 day')\n")
            sim_command = sim_command.lower().strip()
            
            if not sim_command: 
                sim_command = "run 1 day"  # default to run 1 day

            try: 
                if sim_command in ["f", "fin", "finish", "save and finish"]: 
                    # Finishes the simulation environment and saves the progress. 
                    # Example: fin
                    self.save()
                    break

                elif sim_command == "exit": 
                    # Finishes the simulation environment but does not save the progress
                    # and erases all saved data from current simulation. 
                    # Example: exit 
                    shutil.rmtree(simulation_folder) 
                    break 

                elif sim_command == "save": 
                    # Saves the current simulation progress. 
                    # Example: save
                    self.save()

                elif sim_command[:3] == "run":
                    # Runs the number of steps specified in the prompt.
                    num_minutes = parse_command(sim_command)
                    num_steps = int(num_minutes / config.minutes_per_step)
                    pretty_print(f">>> Start running for {num_minutes} minutes ({num_steps} steps).")
                    self.start_server(num_steps)
                    
                elif ("call -- analysis" in sim_command.lower()): 
                    # Starts a stateless chat session with the agent. It does not save 
                    # anything to the agent's memory. 
                    # Ex: call -- analysis Isabella Rodriguez
                    persona_name = sim_command[len("call -- analysis"):].strip() 
                    self.population[persona_name].user_converse_with_persona("analysis")

            except:
                traceback.print_exc()
                print ("Error.")
                pass


    def open_server_with_command(self, sim_command): 
        """
        Open up an interactive terminal prompt that lets you run the simulation 
        step by step and probe agent state. 

        Args: 
            None
            
        Returns
            None
        """
        # <simulation_folder> points to the current simulation folder.
        simulation_folder = f"{config.persona_storage}/{self.simulation_name}"

        while True: 
            #sim_command = input("\nEnter option: (e.g. 'run 1 day', 'run 8 hours'; default: 'run 1 day')\n")
            sim_command = sim_command.lower().strip()
            
            if not sim_command: 
                sim_command = "run 1 day"  # default to run 1 day

            try: 
                if sim_command in ["f", "fin", "finish", "save and finish"]: 
                    # Finishes the simulation environment and saves the progress. 
                    # Example: fin
                    self.save()
                    break

                elif sim_command == "exit": 
                    # Finishes the simulation environment but does not save the progress
                    # and erases all saved data from current simulation. 
                    # Example: exit 
                    shutil.rmtree(simulation_folder) 
                    break 

                elif sim_command == "save": 
                    # Saves the current simulation progress. 
                    # Example: save
                    self.save()

                elif sim_command[:3] == "run":
                    # Runs the number of steps specified in the prompt.
                    num_minutes = parse_command(sim_command)
                    num_steps = int(num_minutes / config.minutes_per_step)
                    pretty_print(f">>> Start running for {num_minutes} minutes ({num_steps} steps).")
                    self.start_server(num_steps)
                    
                elif ("call -- analysis" in sim_command.lower()): 
                    # Starts a stateless chat session with the agent. It does not save 
                    # anything to the agent's memory. 
                    # Ex: call -- analysis Isabella Rodriguez
                    persona_name = sim_command[len("call -- analysis"):].strip() 
                    self.population[persona_name].user_converse_with_persona("analysis")

            except:
                traceback.print_exc()
                print ("Error.")
                pass


def main(fork_name, simulation_name, command):
    # For frontend server
    # test creating new simulation
    #rs = BackendServer(None, "base_the_town")
    # test forking simulation
    #rs = BackendServer("base_the_town", "test")
    parser = argparse.ArgumentParser(description="start/stop GATSim backend")
    parser.add_argument('--fork', type=str,   help='Fork name')
    parser.add_argument('--name', type=str,   help='Simulation name')
    parser.add_argument('--cmd',  type=str,   help='Command string')
    args = parser.parse_args()
    fork_name = args.fork
    simulation_name = args.name
    command = args.cmd
    
    opening = """
  ____    _  _____ ____  _           
 / ___|  / \|_   _/ ___|(_)_ __ ___  
| |  _  / _ \ | | \___ \| | '_ ` _ \ 
| |_| |/ ___ \| |  ___) | | | | | | |
 \____/_/   \_\_| |____/|_|_| |_| |_|
"""
    print(opening)
    print("=======================================Generative-Agent Transport Simulation (GATSim)========================================")
    if "'" or '"' in fork_name:
        fork_name = fork_name.replace("'", "").replace('"', '')
    if "'" or '"' in simulation_name:
        simulation_name = simulation_name.replace("'", "").replace('"', '')
    if "'" or '"' in command:
        command = command.replace("'", "").replace('"', '')
        
    default_fork = "base_the_town"
    #fork_name = input(f"Enter the name of the forked simulation: (default: {default_fork}); type 'none' for creating a new simulation\n").strip()
    if not fork_name:  # If user just presses Enter (empty string)
        fork_name = default_fork  # Set to default value
    elif fork_name.lower() == "none" or '"none':
        fork_name = None
    
    if fork_name:
        print(f">>> Using simulation fork name: {fork_name}")
    else:
        print(f">>> Creating new simulation...")
    
    # Generate default name based on current date and time 
    # Example output: "mar_19_1602"
    default_simulation_name = "sim_" + datetime.now().strftime("%m%d_%H%M")
    # default name: "mar_19_1602" where "1602" is HH:MM
    #simulation_name = input(f"\nEnter the name of this simulation run: ({default_simulation_name})\n").strip()
    # Use default if user just presses Enter
    if not simulation_name:
        simulation_name = default_simulation_name
        print(f">>> Using simulation name: {simulation_name}")
    
    # create backend
    backend = BackendServer(fork_name, simulation_name)
    
    # print simulation info
    # Get list of personas and facilities
    persona_names = list(backend.population.keys())
    pretty_print(f"Initialized {len(persona_names)} personas", 1)
    
    facilities = list(backend.maze.facilities_info.keys())
    pretty_print(f"Available facilities: {len(facilities)}", 1)
    print()
    
    # Print initial state
    pretty_print("\nInitial State:", 1)
    for persona_name in persona_names:
        home_facility = backend.population[persona_name].st_mem.curr_place
        pretty_print(f"{persona_name} is at {home_facility}", 2)
    print()
    
    # run simulation
    backend.open_server_with_command(command)

        


def test():
    # For testing purposes
    # test creating new simulation
    #rs = BackendServer(None, "base_the_town")
    # test forking simulation
    #rs = BackendServer("base_the_town", "test")
    
    default_fork = "base_the_town"
    fork_name = input(f"Enter the name of the forked simulation: (default: {default_fork}); type 'none' for creating a new simulation\n").strip()
    if not fork_name:  # If user just presses Enter (empty string)
        fork_name = default_fork  # Set to default value
    elif fork_name.lower() == "none":
        fork_name = None
    
    if fork_name:
        print(f">>> Using simulation fork name: {fork_name}")
    else:
        print(f">>> Creating new simulation...")
    
    # Generate default name based on current date and time 
    # Example output: "mar_19_1602"
    default_simulation_name = "sim_" + datetime.now().strftime("%m%d_%H%M")
    # default name: "mar_19_1602" where "1602" is HH:MM
    simulation_name = input(f"\nEnter the name of this simulation run: ({default_simulation_name})\n").strip()
    # Use default if user just presses Enter
    if not simulation_name:
        simulation_name = default_simulation_name
        print(f">>> Using simulation name: {simulation_name}")
    
    # create backend
    backend = BackendServer(fork_name, simulation_name)
    
    # print simulation info
    # Get list of personas and facilities
    persona_names = list(backend.population.keys())
    pretty_print(f"Initialized {len(persona_names)} personas", 1)
    
    facilities = list(backend.maze.facilities_info.keys())
    pretty_print(f"Available facilities: {len(facilities)}", 1)
    print()
    
    # Print initial state
    pretty_print("\nInitial State:", 1)
    for persona_name in persona_names:
        home_facility = backend.population[persona_name].st_mem.curr_place
        pretty_print(f"{persona_name} is at {home_facility}", 2)
    print()
    
    # run simulation
    backend.open_server()
    
    
    if False:
        # Create a new simulation (no fork)
        simulation_name = "sim_" + datetime.now().strftime("%m%d_%H%M")
        print(f"Creating new simulation: {simulation_name}")
        
        # Initialize the backend server with no fork
        backend = BackendServer(None, simulation_name)
        
        # Run simulation for a number of steps
        num_steps = 60 * 24  # Run for a good number of steps to see movement
        print(f"\nRunning simulation for {num_steps} steps...")
        backend.start_server(num_steps)
    
    # Print final state after simulation run
    print("\nFinal State:")
    for persona_name in persona_names:
        location = backend.population[persona_name].st_mem.curr_place 
        destination = backend.population[persona_name].st_mem.activity_facility if hasattr(backend.population[persona_name].st_mem, "activity_facility") else "No destination"
        print(f"  {persona_name} is at {location}, destination: {destination}")
    
    # Save final state
    backend.save()
    print("\nSimulation test completed and state saved.")
    
    # Enter interactive mode if needed
    enter_interactive = input("Enter interactive mode? (y/n): ").strip().lower()
    if enter_interactive == 'y':
        print("Entering interactive mode. Type 'help' for available commands.")
        backend.open_server()
    else:
        print("Test completed. Exiting.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="start/stop GATSim backend")
    parser.add_argument('--fork', type=str,   help='Fork name')
    parser.add_argument('--name', type=str,   help='Simulation name')
    parser.add_argument('--cmd',  type=str,   help='Command string')
    args = parser.parse_args()
    fork_name = args.fork
    simulation_name = args.name
    command = args.cmd
    
    main(fork_name, simulation_name, command)