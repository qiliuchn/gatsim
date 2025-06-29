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
import argparse
import copy
from gatsim import config
from gatsim.utils import parse_command, pretty_print, copyanything, convert_time_str_to_datetime
from gatsim.map.maze import Maze
from gatsim.agent.llm_modules.run_prompt import generate_importance_score
from gatsim.agent.memory_modules.long_term_memory import ConceptNode
from gatsim.agent.persona import Persona, initialize_population
# for parallel processing
import concurrent.futures
import threading
from typing import Dict, List, Tuple
import traceback



random.seed(0)

""" 
# Terminology
 - node: node in transportation network graph;
 - link: link in transportation network graph;
 - location: node or link, namely a transportation network graph entity;
 - facility: a place for activity, like Office, Gym;
 - place: location or facility, a maze entity;
 - step: the total number of steps the simulation has already taken;
 - count: the number of steps that the simulation will take for this run. A count down.


# Persona current activity info
 - persona.st_mem.activity_facility: the target facility where activity take places;
 - persona.st_mem.activity_departure_time: the departure time for current activity;
 - persona.st_mem.activity_duration: planned activity duration (including travel time);
 - persona.st_mem.reflect_every: how frequently persona can update its activity plan;
 - persona.st_mem.travel_mode: "drive" or "transit"; if "transit", agent can walk or ride the transit;
 - persona.st_mem.activity_description: string description of the activity.
 - persona.st_mem.planned_path: a list with elements like (next_link, next_mode, next_node), guiding how persona should move on the maze transportation network;
    the first element is popped when persona is entering the next_link; so next_mode/next_node information of this first element also got transferred to mobility event;


# Persona mobility tracking
There are redundancies on mobility tracking to achieve modular design, so that modules will have less dependencies!
They are:
 - 1) Persona will remember where he or she is in the short term memory to facilitate personal cognitive process;
 - 2) Persona movements are also tracked by backend server to simulate traffic flow (mobility events);
 - 3) Persona movements are also tracked by network (maze class) to facilitate realtime state update, inspection (say, update wait time level; impose capacity constraints);
All records are synchronized by simulation core.

Details:
    1) Persona current activity in persona memory
    - persona.st_mem.curr_place: current place of the persona on the transportation network
    - persona.st_mem.curr_status: description of what the persona is doing now (say, "waiting" on link, "staying" in a facility ...)
    
    2) persona mobility tracking in backend simulator
    - we will use mobility events to track persona movements
    - backend_server.mobility_events is a dict keeping track of persona movements
    - Each persona has exactly one mobility event
    - Mobility event is created at the start of the simulation, and updated for each run step.
    - A mobility event is a dict, with keys:
        'name' (str): persona name
        'place' (str): node, link, or facility name
        'next_node' (str): next node of the persona if on link; None if agent is at a node or facility
        'status' (str): "driving" (on a road link) / "walking" (on a a road link) / "riding" (the metro) / "waiting" (at a link or node or facility) / "staying" (at a facility)
        'start_time' (datetime): start time of the event
        'description' (str): description of the event
        'moved' (bool): whether this persona has already been moved in the current run step.

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
    - queue lists (list of persona names) are stored on the network entities (facility / node / link);
    - queue lists are updated with mobility events updates;
    - mobility events and queue lists are all saved in storage;
    - queue list is a list of persona names; queue lists includes:
        - maze.links_info[link]['driving'][i]  
            # number of moving personas on a road link with direction i (i = 0, 1)
        - maze.links_info[link]['riding'][i]
            # number of moving personas on a metro link with direction i (i = 0, 1)
        - maze.links_info[link]['waiting'][i] 
            # if the link is road link, it means the number of personas waiting to drive through the road link for direction i (i = 0, 1)
            # if the link is metro link, it means the number of personas waiting to board the metro link for direction i (i = 0, 1)
        - maze.nodes_info[node]['waiting']  
            # number of personas waiting at a node to enter next link or facility
        - maze.facilities_info[facility]['staying']
            # number of personas staying in the facility, engaged in their planned activities;
        - maze.facilities_info[facility]['waiting']
            # number of personas waiting at the facility


# Transit modeling
Agent can start to traverse a metro link when the metro train arrives at the station
Each train stop at the station for one time step. This extra stopping time should be considered in making transit schedules!

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



# Travel experiences are added to persona long term memory (lt_mem) in backend script.
See:
#===Add link wait experience to memory===
...
#===Add trip experience to memory===
...
#===Add activity experience to memory===
...


# simulation meta.json example:
{
    "fork_name": null,
    "simulation_name": "sim_0522_0909",
    "start_date": "2025-03-10 00:00:00",
    "curr_time": "2025-03-10 00:00:00",
    "minutes_per_step": 1,
    "maze_name": "The town",
    "persona_names": [
        "Isabella Rodriguez",
        "Sophia Nguyen",
        "Daniel Nguyen"
    ],
    "step": 0
}


# Cache
Simulation storage is updated at the end of each simulation step; they are used for logging and reloading the simulation. All chats, all plans, all reflections are stored.
V.S. 
Cache files (for movements, messages) are updated immediately after movements, chatting, reflection happened within a simulation step; 
They are used for dynamic visualization by Web UI. They are dynamically updated. 
This cache folder is updated during each simulation step.
 - gatsim/cache/curr_meta.json stores current step meta information.
 - gatsim/cache/curr_plans.json stores current persona plans.
 - gatsim/cache/curr_messages.json stores current persona chats and reflection information.
 - gatsim/cache/curr_movements.json stores current step movements.


# Concurrency
Race conditions:
    1) a persona only affect other personas memory though chatting and add_concept_node method in plan()
    2) a persona changes cache files
so we:
    1) add population lock to add_concept_node method in long term memory
    2) add lock to cache modifying block of codes

Note:
client = OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"), base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",)
OpenAI client uses httpx internally (thread-safe HTTP library)
Each API call creates a separate HTTP request
Multiple threads can safely call client.chat.completions.create() simultaneously
    Thread 1: persona.plan() → client.chat.completions.create() → HTTP Request A
    Thread 2: persona.plan() → client.chat.completions.create() → HTTP Request B  
    Thread 3: persona.plan() → client.chat.completions.create() → HTTP Request C
All requests go to the API server independently and concurrently


# Notes about travel mode notations:
<link_type> of link in network: road/metro, 
    where "road" means persona can drive or walk through the road link; "metro" means persona can only ride train through the metro link;
<travel_mode> in activity plan: drive/transit, where "transit" means persona can walk or use transit to reach the activity facility;
link traversing mode (path component): drive/walk/ride, where "walk" means walking through the road link, "ride" means riding train through the metro link.
link queue types: driving/walking/riding/waiting
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
        # locks for parallel execution        
        self._population_lock = threading.RLock()  # For population access
        config.lock = self._population_lock
            
        if fork_name:  # if fork_name is not empty, load the fork
            print('>>> Creating fork simulation...')
            self.fork_name = fork_name
            fork_folder = f"{config.simulation_storage}/{self.fork_name}"

            # <simulation_name> indicates our current simulation. The first step here is to  
            # copy everything that's in <fork_name>, but edit its meta.json's fork variable. 
            self.simulation_name = simulation_name
            simulation_folder = f"{config.simulation_storage}/{self.simulation_name}"
            self.simulation_folder = simulation_folder
            copyanything(fork_folder, simulation_folder)

            with open(f"{self.simulation_folder}/meta.json") as json_file:  
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
                persona_folder = f"{self.simulation_folder}/personas/{persona_name}"
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
                    raise  ValueError(f"Error loading movements data: {str(e)}")
            else:
                raise  ValueError(f"Error! No movements file found at {movements_file}!")
            
        else:  # create a new simulation from scratch
            # clean output file only if starting a new simulation
            if config.output_redirect_to_file:
                with open(config.redirect_file, 'w') as f:
                    f.write("")
                
            # mainly load settings from config files
            print('>>> Creating a new simulation by loading population and config files...')
            simulation_meta = dict()
            self.fork_name = None
            simulation_meta['fork_name'] = None
            self.simulation_name = simulation_name
            simulation_meta['simulation_name'] = self.simulation_name
            simulation_folder = f"{config.simulation_storage}/{self.simulation_name}"
            self.simulation_folder = simulation_folder
            os.makedirs(self.simulation_folder, exist_ok=True)
            
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
            self.population = initialize_population(f'{config.agent_path}/population_info.json', self.simulation_folder)
            simulation_meta['persona_names'] = list(self.population.keys())
            
            # initialize cache
            curr_movements_f = f"{config.simulation_cache}/curr_movements.json"
            curr_movements = dict()
            curr_movements['mobility_events'] = dict()
            curr_movements['meta'] = dict()
            curr_movements['queues'] = dict()
            for persona_name in self.population.keys():
                curr_movements['mobility_events'][persona_name] = None
            with open(curr_movements_f, "w") as f:
                json.dump(curr_movements, f, indent=4)
            
            # initialize mobility events
            # at the start of the day, agents stay at home
            self.mobility_events = {}
            for persona_name in simulation_meta['persona_names']:
                self._initialize_mobility_events(persona_name, generate_random_plan=False)
                # Only set generate_random_plan=True if you want to test backend server - initialize personas with random activity plans
                
            self.save()  # save the newly created simulation

        # Configure thread pool size based on your needs
        # Start with 4-8 threads, adjust based on your LLM API rate limits
        self.max_planning_threads = min(config.max_planning_threads, len(self.population))
        # add lock
        for persona_name in self.population:
            self.population[persona_name]._population_lock = self._population_lock
            self.population[persona_name].lt_mem._population_lock = self._population_lock

        # <server_sleep> denotes the amount of time that our while loop rests each cycle; this is to not kill our machine. 
        self.server_sleep = config.server_sleep
        


    def _initialize_mobility_events(self, persona_name, generate_random_plan=False):
        """
        Initialize backend server movement plans when creating a new simulation
        Personas all start with staying at home by  default.
        
        If generate_random_plan = True, then the persona will generate a random activity. For testing purposes only.
        
        Args:
            persona_name (str): Name of the persona to initialize
            generate_random_plan (bool): true if random persona plan needs to be generated; only for backend server testing
        """
        persona = self.population[persona_name]
        
        # Get home_facility
        home_facility = persona.st_mem.home_facility
        persona.st_mem.curr_place = home_facility
        
        if generate_random_plan:
            # generate random plan for agent for testing purpose
            
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
        
        # Initialize facility's 'staying' list if it doesn't exist
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
        
        if generate_random_plan:
            pretty_print(f"Initialized {persona_name} with plan to go from {home_facility} to {target_facility} at {persona.st_mem.activity_departure_time.strftime('%H:%M')} using {'drive' if travel_mode else 'transit'}", 1)




    def _plan_persona_safe(self, persona_name: str) -> Tuple[str, bool, str]:
        """
        Thread-safe wrapper for persona planning.
        NO lock around the entire plan() call - only around critical sections inside plan().
        """
        try:
            persona = self.population[persona_name]
            # Call plan() without any locks - let it run concurrently
            # The locks will be applied inside specific methods that need protection
            persona.plan(self.maze, self.population)
            
            return (persona_name, True, "")
            
        except Exception as e:
            error_msg = f"Error planning for {persona_name}: {str(e)}\n{traceback.format_exc()}"
            pretty_print(error_msg, 2)
            return (persona_name, False, error_msg)


    def _parallel_persona_planning(self) -> Dict[str, Tuple[bool, str]]:
        """
        Execute persona planning in parallel WITHOUT blocking LLM calls.
        Returns a dictionary mapping persona names to (success, error_message) tuples.
        Note: do not add retry mechanism here. retry mechanism is added at llm call invokes.
        """
        # Get list of personas that can update their plans
        personas_to_plan = []
        pretty_print('Persona potential to update plans:', 1)
        for persona_name, persona in self.population.items():
            can_update_plan = self._check_if_persona_can_update_plan(persona_name)
            if can_update_plan:
                personas_to_plan.append(persona_name)
                pretty_print()
                pretty_print(f">>> {persona.st_mem.name} - scheduled for plan update", 2)
        
        if not personas_to_plan:
            return {}
        
        num_workers = min(self.max_planning_threads, len(personas_to_plan))
        pretty_print()
        pretty_print(f"\n>>> Parallel planning: {len(personas_to_plan)} personas, {num_workers} threads", 1)
        results = {}  # This dictionary will store the outcome of each persona's planning:
        # Key: persona_name (string)
        # Value: (success, error_msg) tuple
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:  # Creates a pool of num_workers threads
            # Submit all planning tasks at once
            # This creates a dictionary mapping:
            # Key: Future object (represents a running task)
            # Value: persona_name (so we know which persona this task belongs to)
            future_to_persona = {
                executor.submit(self._plan_persona_safe, persona_name): persona_name
                for persona_name in personas_to_plan
            }
            
            # Collect results as they complete
            # as_completed() returns futures as they finish (not in submission order)
            for future in concurrent.futures.as_completed(future_to_persona):
                persona_name = future_to_persona[future]
                # Process Each Completed Task
                try:
                    result_persona_name, success, error_msg = future.result(timeout=config.planning_timeout)  # 10 minute timeout
                    results[result_persona_name] = (success, error_msg)
                    status = "✅" if success else "❌"
                    pretty_print(f"{status} {result_persona_name} planning completed", 2)
                    #if not success:
                    #    pretty_print(f"{error_msg}", 1)
                    #    exit(1)
                except concurrent.futures.TimeoutError:
                    pretty_print(f"Error 002: ⏰ {persona_name} planning timed out", 2)
                    results[persona_name] = (False, "Timeout")
                    #exit(1)
                except Exception as e:
                    pretty_print(f"Error 003: 💥 {persona_name} unexpected error: {e}", 2)
                    results[persona_name] = (False, str(e))
                    #exit(1)
        success_count = sum(1 for success, _ in results.values() if success)
        pretty_print(f">>> Planning completed: {success_count}/{len(results)} successful", 1)
        if success_count == len(results):
            pretty_print("✅ All planning successful", 1)
        else:
            pretty_print("❌ Some planning failed", 1)
            raise Exception("Some planning failed")
        return results
    

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
        # Note: link queues do not distinguish direction
        # direction can be inferred from persona mobility_events
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
        # Fill in mobility_events
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
        
        # Fill in queue information
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
        pretty_print(f">>> Start simulation (fork: {self.fork_name} name: {self.simulation_name}) for {int_counter} steps...", 0)
        
        # Prepare cache files
        # These files are used for visualization purposes
        # 1) meta (Note: this is not for simulation meta storage; this is for cache!)
        curr_meta_f = f"{config.simulation_cache}/curr_meta.json"
        curr_meta = dict() 
        curr_meta["simulation_name"] = self.simulation_name
        curr_meta["curr_step"] = self.step
        curr_meta["maze_name"] = self.maze.maze_name
        curr_meta["curr_time"] = self.curr_time.strftime("%Y-%m-%d %H:%M:%S")
        curr_meta["persona_names"] = list(self.population.keys())
        with open(curr_meta_f, "w") as f:
            json.dump(curr_meta, f, indent=4)
        # 2) plans
        curr_plans_f = f"{config.simulation_cache}/curr_plans.json"
        curr_plans = dict()
        for persona_name in self.population.keys():
            curr_plans[persona_name] = None
        with open(curr_plans_f, "w") as f:
            json.dump(curr_plans, f, indent=4)
        # 3) chats
        curr_messages_f = f"{config.simulation_cache}/curr_messages.json"
        curr_messages = dict()
        for persona_name in self.population.keys():
            curr_messages[persona_name] = None
        with open(curr_messages_f, "w") as f:
            json.dump(curr_messages, f, indent=4)
        
        # The main while loop of simulation. Iterate over simulation run steps.        
        while int_counter > 0: 
            # Done with this iteration if <int_counter> reaches 0. 
            pretty_print("-" * 80)
            pretty_print(f">>> Step: {self.step} | counter: {int_counter} | Current simulation time: {self.curr_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
            #====================================GATSIM Core=========================================================
            # Gatsim core step:
            # (Gatsim core) step 1. Generate/revise plans if needed;
            # (Gatsim core) step 2. Update activity if needed;
            # (Gatsim core) step 3. Movements on network;
            # (Gatsim core) step 4. Reflect on experiences if needed;
            # (Gatsim core) step 5. Save and advance simulation.
            
            #======================(Gatsim core) step 1. Generate activity plan===========================
            """
            # Check all persona whether they need to a make new activity plan or they can revise the activity plans
            # does the event trigger new decision from agent at this step? if so, invoke persona.plan() method
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
            # old code
            '''
            for persona_name, persona in self.population.items():
                can_update_plan = self._check_if_persona_can_update_plan(persona_name)
                if can_update_plan:
                    #persona.plan_for_test(self.maze, self.population)
                    pretty_print()
                    pretty_print(f">>> {persona.st_mem.name} curr status: {persona.st_mem.curr_status} - now update plan", 1)
                    persona.plan(self.maze, self.population)
            '''
            # new code, parallel planning
            self._parallel_persona_planning()
                    
            #=========================(Gatsim core) step 2. Update current activity=======================
            for persona_name, persona in self.population.items():
                departure_time = persona.st_mem.activity_departure_time
                planned_duration = persona.st_mem.activity_duration
                if persona.st_mem.curr_place == persona.st_mem.activity_facility \
                    and (planned_duration == None or departure_time + planned_duration == self.curr_time):
                    # Update persona activity when:
                    # his or her current activity is done
                    #  1) planned_duration == None means leave up arrival, like dropping off kid at School
                    #  2) departure_time + planned_duration == self.curr_time means the activity is done
                    pretty_print()
                    pretty_print(f">>> {persona.st_mem.name} curr status: {persona.st_mem.curr_status} - now finished current activity; update activity", 1)
                    persona.update_activity(self.maze)
                else:
                    # 3) the agent is halfway way to the target facility, but next activity departure time is due; this can happens due to traffic congestion, etc.
                    # 4) it's possible that persona.st_mem.activity_index == -1, current activity is interrupted by the agent; namely the agent changed its mind on the way;
                    current_plan = persona.st_mem.revised_plans[-1]['plan'] if persona.st_mem.revised_plans else persona.st_mem.original_plans[-1]['plan']
                    if persona.st_mem.activity_index + 1 <= len(current_plan) - 1:
                        # to make sure there is a next activity
                        next_activity = current_plan[persona.st_mem.activity_index + 1]
                        next_activity_departure_time = next_activity[1]
                        if next_activity_departure_time != 'none':
                            next_activity_departure_time = convert_time_str_to_datetime(persona.st_mem.curr_time, next_activity_departure_time)
                            if self.curr_time >= next_activity_departure_time:  # next activity departure time is due
                                pretty_print()
                                pretty_print(f">>> {persona.st_mem.name} curr status: {persona.st_mem.curr_status} next activity: {next_activity} - now interrupt current activity; update activity", 1)
                                # we need to pass next node info to find the shortest path when agent is on the link
                                next_node = None
                                if persona.st_mem.curr_place in self.maze.links_info:
                                    next_node = self.mobility_events[persona_name]['next_node']
                                persona.update_activity(self.maze, next_node)
                          
            #========================(Gatsim core) step 3. Simulate Mobility on Network======================
            """
            Mobility simulation process (movements on network):
            Now we describe the transport simulation process.
            Vehicle traversal over road link is queue-based. Road link has capacity; new vehicles can enter only when there is capacity left.
            Metro run according to transit schedule. Persona can only board the metro when the train arrives (maze.links_info[link]['arrival'][i] is true for direction i).
            Personas unable to drive or board the train need to wait at the link. Personas follow first-in, first-out (FIFO) rules to traverse links.
            All time will be represented by datetime object. 
            At the start of the simulation, initialize all personas to have mobility event "staying" at home_facility;
            The detailed simulation running process for each run step is as follows:
            
            (Movement on network) step 3.1: handling traversing events (link to node or continue to travel on link)
                 - Case 1: Move traveling personas from link to node when traversal has finished
                Check all mobility events of status "walking", "driving", "riding"
                    - for a driving persona, if his or her traversal time equal driving travel time (self.links_info[link]['travel_time'][i]), move him or her to next_node by changing his or her mobility events from "driving" at link to "waiting" at node; also update queue lists;
                    - for a riding persona, if his or her traversal time equal riding travel time (self.links_info[link]['travel_time'][i]), move him or her to next_node by changing his or her mobility events from "riding" at link to "waiting" at node; also update queue lists;
                    - for a walking persona, if his or her traversal time equal walking travel time (self.links_info[link]['travel_time'][i] * config.walk_time_factor), move him or her to next_node by changing his or her mobility events from "walking" at link to "waiting" at nodes; also update queue lists;
                Update these persona mobility events to have "moved" being True;
                 
                 - Case 2: if traversal has not finished
                For personas whose traversing is not finished; make no changes to their mobility events; meaning that one more time step has passed as they continue to travel on the link;
                Update these persona mobility events to have "moved" being True;
            
            (Movement on network) step 3.2: handling departure events (facility to node)
                Move personas from facility to node when departure times are due
                Check persona with "moved" being false that are at a facility (persona.st_mem.curr_place) and their planned activities departure time (persona.st_mem.activity_departure_time) is reached,
                move them from the facility to the facility's corresponding node by changing mobility event of status "staying" (or maybe "waiting") at facility to "waiting" at a node;
                Update facilities staying list (self.facilities_info[facility]['staying']); Update node waiting list (self.nodes_info[node]['waiting']);
                Update these persona mobility events to have "moved" being True;
                
            (Movement on network) step 3.3: handling finished events (node to facility)
                Step 3.3.1: Move personas who are at nodes and have finished their trips to facility wait queues
                Check all personas waiting at a node with "moved" being false; 
                Check if their planned trip is over (self.maze.facility2node(persona.st_mem.activity_facility) == self.mobility_events[persona_name]['place'])
                Add them to the facility wait queue (self.facilities_info[persona.st_mem.activity_facility]['waiting']
                
                Step 3.3.2: Check their target facility capacity (maze.facilities_info[facility]['realtime_capacity']) and number of people staying over there (maze.facilities_info[facility][staying]);
                then move them to facility to 'staying' or still 'waiting' at the facility, by changing their "waiting" at node mobility event to "staying" or retain "waiting" at facility mobility event;
                Update these persona mobility events to have "moved" being True;
            
            (Movement on network) step 3.4: handling link entering events (node to link)
                Step 3.4.1: Move personas waiting at a node to next_link
                Check all mobility events of status "waiting" at a node with "moved" being false;
                Pop (next_link, next_mode, next_node) from persona.st_mem.planned_path;
                Update mobility event by:
                 - Case 1: if this persona want to drive through this link, change this persona mobility event from "waiting" at node to "waiting" at the link (self.links_info[link]['waiting']);
                 - Case 2: if this persona want to riding through this link, change this persona mobility event from "waiting" at node to "waiting" at the link (self.links_info[link]['waiting']);
                 - Case 3: if this personas want to walk through the link, change this persona mobility event from waiting at the node to "walking" at link;
                
                Step 3.4.2: Move personas waiting at a link to traversing (waiting at link to traversing link)
                 - Case 1: Check all road links wait list: 
                 if the number of personas driving on the link (#driving) < link capacity (self.links_info[link]['realtime capacity]), 
                 move min(#waiting, link capacity - #driving) many personas from waiting at link to driving at link;
                 the rest personas need to continue "waiting" at link;
                 
                 - Case 2: Check all metro links wait list: 
                 if a metro arrives at a node, move min(metro link realtime capacity, #waiting) many personas with from "waiting" at link to "riding" at link;
                 the rest personas continue "waiting" at link;
                
                Update these persona mobility event to have "moved" being True;
                 
            (Movement on network) step 3.5: Update network and facility states for personas to perceive:
                 - Update road link 'wait_time' attribute;
                 - Update facility 'wait_time' and "crowdedness" attributes;
                 - Reset all persona moved to be False for next run step.

            (Movement on network) step 3.6: Check each agent has a path to follow when traveling (failsafe)
                 
                 
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
             - maze.links_info[link]['realtime_capacity'][i]  
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
            # (Movement on network) Step 3.0: Update the maze state for the current time
            # this is for loading NetworkEvents, like car crash, transit schedule, which may affects capacity of links
            # Note: update at the start of the simulation step, otherwise agent may not be able to board the metro
            self.maze.update(self.curr_time)
            
            # (Movement on network) step 3.1: Handling traversing events (link to node or continue to travel on link)
            self._handle_traversing_events()
            
            # (Movement on network) step 3.2: Handling departure events (facility to node) and finished events (node to facility)
            self._handle_departure_events()
            
            # (Movement on network) step 3.3: Handling finished events (node to facility waiting, facility waiting to facility staying)
            self._handle_finished_events()
            
            # (Movement on network) step 3.4: Handling link entering events (node to link)
            self._handle_link_entering_events()
            
            # (Movement on network) step 3.5: Update network and facility states for personas to perceive
            self._reset_state()
            
            # (Movement on network) step 3.6: Check each agent has a path to follow when traveling (failsafe)
            self._check_path()
            
            #=====================(Gatsim core) step 4. Reflect Daily Experiences========================
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
                    pretty_print()
                    pretty_print(f">>> {persona.st_mem.name} curr status: {persona.st_mem.curr_status} - now reflecting on daily experiences at the end of the day", 1)
                    persona.daily_reflection(self.maze)
                    persona.lt_mem.clean_up_memory()  # clean up memory if necessary
                    
                    # failsafe
                    # if persona didn't manage to get to back home by the end of the day, telescope them home; and print error code
                    if persona.st_mem.curr_place != persona.st_mem.home_facility:
                        pretty_print(f"Error 304: {persona.st_mem.name} failed to get home at the end of the day. Failsafe triggered. Returning home.", 1)
                        self._teleport_home(persona)
            
            #====================(Gatsim core) step 5. Save and Advance Simulation======================
            # Advance simulation step/time
            # After this cycle, the world takes one step forward, and the 
            # current time moves by <minutes_per_step> amount. 
            self.step += 1
            int_counter -= 1
            self.curr_time += timedelta(minutes=self.minutes_per_step)  # backend time updated
            for persona in self.population.values():
                persona.st_mem.curr_time = self.curr_time  # persona st_mem time updated
                persona.lt_mem.curr_time = self.curr_time  # persona lt_mem time updated
            
            # save meta data, memory and movements
            # first advance time, then save
            # so, if you run for one day (1440 minutes),
            # the last movements file is 1440.json
            # and its time is: the start of next day.
            self.save()
            
            # clean cached chats
            cache_chat_f = f"{config.simulation_cache}/curr_chats.json"
            if os.path.exists(cache_chat_f):
                os.remove(cache_chat_f)
            
            # also update cache
            # save cache meta
            curr_meta_f = f"{config.simulation_cache}/curr_meta.json"
            curr_meta = dict() 
            curr_meta["simulation_name"] = self.simulation_name
            curr_meta["curr_step"] = self.step
            curr_meta["maze_name"] = self.maze.maze_name
            curr_meta["curr_time"] = self.curr_time.strftime("%Y-%m-%d %H:%M:%S")
            curr_meta["persona_names"] = list(self.population.keys())
            with open(curr_meta_f, "w") as f:
                json.dump(curr_meta, f, indent=4)
                
            # Sleep so we don't burn our machines. 
            time.sleep(self.server_sleep)
            #====================================GATSIM Core End======================================================


    # Private methods for simulating queue-based traffic
    # (Movement on network) 3.1) handle link traversing events
    # (Movement on network) 3.2) handle departure events
    # (Movement on network) 3.3) handle finished events
    # (Movement on network) 3.4) handle link entering events
    def _handle_traversing_events(self):
        """
        (Movement on network) Step 3.1: Handle traversing events (link to node or continue to travel on link)
        - Move personas from link to node when traversal is finished
        - Otherwise, update traversal time for personas still on links
        """
        # Iterate through all mobility events
        for persona_name, event in self.mobility_events.items():
            persona = self.population[persona_name]
            
            # Skip personas that have already moved in this step or are not traversing links
            if event['moved'] or event['status'] not in ["driving", "riding", "walking"]:
                continue
            
            # Get the current link
            link_name = event['place']
            if link_name not in self.maze.links_info:
                raise  ValueError(f"Link {link_name} not found in maze.links_info")
                
            # Determine which direction the persona is traveling (0 or 1)
            endpoints = self.maze.links_info[link_name]['endpoints']
            next_node = event['next_node']
            direction = 1 if next_node == endpoints[0] else 0
            
            # Calculate time spent on link
            time_spent = int((self.curr_time - event['start_time']).total_seconds() / 60)  # in minutes
            
            # Get applicable travel time based on mode
            if event['status'] == "walking":
                travel_time = self.maze.links_info[link_name]['travel_time'] * config.walk_time_factor
            else:  # driving or riding
                travel_time = self.maze.links_info[link_name]['travel_time']
            
            # Check if traversal is complete
            if time_spent >= travel_time:
                # Move persona from link to node
                
                # 1) Remove from link queue
                if event['status'] == "driving" and persona_name in self.maze.links_info[link_name]['driving'][direction]:
                    self.maze.links_info[link_name]['driving'][direction].remove(persona_name)
                elif event['status'] == "riding" and persona_name in self.maze.links_info[link_name]['riding'][direction]:
                    self.maze.links_info[link_name]['riding'][direction].remove(persona_name)
                elif event['status'] == "walking" and persona_name in self.maze.links_info[link_name]['walking'][direction]:
                    self.maze.links_info[link_name]['walking'][direction].remove(persona_name)
                
                # 2) Add to node waiting queue
                if next_node not in self.maze.nodes_info:
                    raise  ValueError(f"Warning: Next node {next_node} not found for {persona_name}")
                    
                self.maze.nodes_info[next_node]['waiting'].append(persona_name)
                persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory};  currently at node {next_node}; planned path left: {persona.st_mem.planned_path};"
                
                # 3) Update mobility event
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': next_node,
                    'next_node': None,
                    'status': "waiting",
                    'start_time': self.curr_time,
                    'description': event['description'],  # Keep the same activity description
                    'moved': True  # Mark as moved; so this agent will not be moved during this step
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
        
                
                # 4) Update persona current place
                persona.st_mem.curr_place = next_node

            else:
                # Persona continues traversing the link
                self.mobility_events[persona_name]['moved'] = True  # mark as moved
                persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory};  currently traversing link {link_name}; planned path left: {persona.st_mem.planned_path};"
                
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
        (Movement on network) Step 3.2: Handle departure events (facility to node)
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
                raise ValueError(f"Facility {facility_name} not found in maze")
                
            # Check if departure time has arrived
            if hasattr(persona.st_mem, "activity_departure_time") and \
            self.curr_time == persona.st_mem.activity_departure_time:
                # create trip variables to record the trip
                persona.st_mem.trip_start_facility = persona.st_mem.curr_place
                persona.st_mem.trip_trajectory = []  # initialize trajectory
                # record persona travel trajectory; append as persona travel on the network.
                # format: same as the planned path:
                # [(next_link, next_mode, next_node),...]
                
                # if the next activity happens in the same facility, we don't need to move the persona
                if persona.st_mem.curr_place == persona.st_mem.activity_facility:
                    continue
                
                # Get the node corresponding to this facility
                node_name = self.maze.facility2node.get(facility_name)
                if not node_name:
                    raise  Exception(f"Error: No node found for facility {facility_name}")
                    
                # 1) Remove from facility staying list
                if persona_name in self.maze.facilities_info[facility_name]['staying']:
                    self.maze.facilities_info[facility_name]['staying'].remove(persona_name)
                    
                # 2) Add to node waiting list
                self.maze.nodes_info[node_name]['waiting'].append(persona_name)
                
                # 3) Update mobility event and persona state
                persona.st_mem.curr_place = node_name
                persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory}; currently at node {node_name}; planned path left: {persona.st_mem.planned_path};"
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': node_name,
                    'next_node': None,
                    'status': "waiting",
                    'start_time': self.curr_time,
                    'description': f"going to {persona.st_mem.activity_facility}" if hasattr(persona.st_mem, "activity_facility") else "leaving",
                    'moved': True  # Mark as moved
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
        (Movement on network) Step 3.3: Handle finished events (node to facility waiting, facility waiting to facility staying)
        - 3.3.1) Move personas from facility to node when departure times are due; add them to facility wait list;
        - 3.3.2) Move some personas from wait list to facility staying list, according to the available capacity.
        """
        # Step 3.3.1: Handle finished events (node to facility waiting)
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
            content = f"{persona_name} travels from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility} by travel mode {persona.st_mem.travel_mode}; start time is {start_time_str}; trip time is {trip_time} minutes"
            keywords = [f"{persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}", f"{persona.st_mem.travel_mode}"]
            spatial_scope = f"{persona.st_mem.trip_start_facility}, {persona.st_mem.activity_facility}"
            for seg in persona.st_mem.trip_trajectory:
                road_name = seg[0].split('_')[0] + '_' + seg[0].split('_')[1]
                spatial_scope += ', ' + road_name
            time_scope = [persona.st_mem.activity_departure_time.time(), self.curr_time.time()]
            importance = generate_importance_score(persona, self.maze, "event", content)
            node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
            persona.lt_mem.add_concept_node(node)
            # re-initialize trip variables
            persona.st_mem.trip_start_facility = None
            persona.st_mem.trip_trajectory = None
            
            # 1) Remove from node waiting list
            if persona_name in self.maze.nodes_info[node_name]['waiting']:
                self.maze.nodes_info[node_name]['waiting'].remove(persona_name)
            
            # 2) persona join wait queue at facility
            self.maze.facilities_info[target_facility]['waiting'].append(persona_name)
            new_status = "waiting"
            
            # 3) Update mobility event and persona state
            persona.st_mem.curr_place = target_facility
            persona.st_mem.curr_status = f"{persona_name} just finished the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; waiting at {persona.st_mem.activity_facility} now"
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
            
            # 4) Reset planned path since destination if reached
            persona.st_mem.planned_path = []
            
        # Step 3.3.2: Handle finished events (facility waiting to facility staying)
        for facility_name in self.maze.facilities_info:
            current_occupancy = len(self.maze.facilities_info[facility_name]['staying'])
            available_capacity = self.maze.facilities_info[facility_name]['realtime_capacity'] - current_occupancy
            
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
                #===Add activity experience to memory===
                type = 'event'
                created = self.curr_time
                if wait_time >= 5:
                    start_time_str = self.mobility_events[persona_name]['start_time'].strftime("%a %Y-%m-%d %H:%M")
                    content = f"{persona_name} arrived at {facility_name} at {start_time_str}; and waits for {wait_time} minutes in queue before starting the activity."
                    keywords = ["wait", facility_name]
                    spatial_scope = facility_name
                    time_scope = [self.mobility_events[persona_name]['start_time'].time(), self.curr_time.time()]
                    importance = generate_importance_score(persona, self.maze, "event", content)
                    node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
                    persona.lt_mem.add_concept_node(node)
                
                # Update mobility event and persona state
                persona.st_mem.curr_place = facility_name
                persona.st_mem.curr_status = f"After waiting for {wait_time} minutes at the facility, {persona_name} is currently staying at facility {facility_name} engaged in the target activity;"
                # Note: add facility wait time to the status
                self.mobility_events[persona_name] = {
                    'name': self.mobility_events[persona_name]['name'],
                    'place': facility_name,
                    'next_node': None,
                    'status': "staying",
                    'start_time': self.curr_time,
                    'description': f"Staying at {facility_name}",
                    'moved': True  # now mark as moved
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
                
            # Mark remaining waiting personas as moved (they've been processed) although they haven't been moved physically
            for persona_name in self.maze.facilities_info[facility_name]['staying']:
                if not self.mobility_events[persona_name]['moved']:
                    self.mobility_events[persona_name]['moved'] = True
            

    def _handle_link_entering_events(self):
        """
        (Movement on network) Step 3.4: Handle link entering events (node to link)
        - Move personas from node to link waiting queue (Step 4.1)
        - Move personas from link waiting queue to traversing the link (Step 4.2)
        """
        # Step 3.4.1: Move personas waiting at a node to the next link's waiting queue
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
            
            # add to trip trajectory
            persona.st_mem.trip_trajectory.append((next_link, next_mode, next_node))
            
            # Verify the next link exists
            if next_link not in self.maze.links_info:
                raise ValueError(f"Link {next_link} not found in maze")
                #pretty_print(f"Warning: Link {next_link} not found in maze for {persona_name}", 1)
                #continue
                
            # Determine the direction for this link
            endpoints = self.maze.links_info[next_link]['endpoints']
            
            # Direction is 0 if going from endpoints[0] to endpoints[1], otherwise 1
            # so that we can add agent to the correct directional queue
            direction = 0 if (node_name == endpoints[0] and next_node == endpoints[1]) else 1
            
            # Based on the next_mode, update the mobility event and queue lists
            if next_mode == "drive":
                if self.maze.links_info[next_link]['type'] != 'road':
                    raise ValueError(f"Cannot drive on non-road link {next_link}")
                    #pretty_print(f"Warning: Cannot drive on non-road link {next_link}", 1)
                    #continue
                    
                # Remove from node waiting queue
                if persona_name in self.maze.nodes_info[node_name]['waiting']:
                    self.maze.nodes_info[node_name]['waiting'].remove(persona_name)
                    
                # Add to link waiting queue
                self.maze.links_info[next_link]['waiting'][direction].append(persona_name)
                
                # Update mobility event and persona state
                persona.st_mem.curr_place = next_link
                persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory}; currently waiting at link {next_link}; planned path left: {persona.st_mem.planned_path}"
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "waiting",  # Will be changed to "driving" in Step 4.2 if capacity allows
                    'start_time': self.curr_time,
                    'description': event['description'],
                    'moved': False  # Set to False so this persona can be moved in step 4.2
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
                    'status': "waiting",
                    'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'description': event['description'],
                    'moved': False,
                    'coord': coord
                }
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Pop the next move from the planned path
                persona.st_mem.planned_path.pop(0)
                
            elif next_mode == "ride":
                if self.maze.links_info[next_link]['type'] != 'metro':
                    raise ValueError(f"Cannot ride on non-metro link {next_link}")
                    #pretty_print(f"Warning: Cannot ride on non-metro link {next_link}", 1)
                    #continue
                    
                # Remove from node waiting queue
                if persona_name in self.maze.nodes_info[node_name]['waiting']:
                    self.maze.nodes_info[node_name]['waiting'].remove(persona_name)
                    
                # Add to link waiting queue
                self.maze.links_info[next_link]['waiting'][direction].append(persona_name)
                
                # Update mobility event and persona state
                persona.st_mem.curr_place = next_link
                persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory}; currently waiting at link {next_link}; planned path left: {persona.st_mem.planned_path};"
                self.mobility_events[persona_name] = {
                    'name': event['name'],
                    'place': next_link,
                    'next_node': next_node,
                    'status': "waiting",  # Will be changed to "riding" in Step 4.2 if metro arrives
                    'start_time': self.curr_time,
                    'description': event['description'],
                    'moved': False  # Set to False so this persona can be moved in step 4.2
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
                persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory}; currently walking on link {next_link}； planned path left: {persona.st_mem.planned_path};"
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
                
        # Step 3.4.2: Move personas from link waiting queue to traversing the link
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
                    capacity = self.maze.links_info[link_name]['realtime_capacity'][direction]
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
                        
                        #===Add link wait experience to memory===
                        type = 'event'
                        created = self.curr_time
                        wait_time = int((self.curr_time - self.mobility_events[persona_name]['start_time']).total_seconds() / 60)
                        if wait_time >= 5:
                            start_time_str = self.mobility_events[persona_name]['start_time'].strftime("%a %Y-%m-%d %H:%M")
                            content = f"{persona_name} waits at {link_name}; start time is {start_time_str}; wait time is {wait_time} minutes"
                            keywords = ["wait", link_name]
                            spatial_scope = link_name
                            time_scope = [self.mobility_events[persona_name]['start_time'].time(), self.curr_time.time()]
                            importance = generate_importance_score(persona, self.maze, "event", content)
                            node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
                            persona.lt_mem.add_concept_node(node)
                        
                        # Update mobility event and persona state
                        persona.st_mem.curr_place = link_name
                        persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory}; after waiting for {wait_time} minutes, currently driving on link {link_name}; planned path left: {persona.st_mem.planned_path};"
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
                        capacity = self.maze.links_info[link_name]['realtime_capacity'][direction]
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
                            
                            #===Add link wait experience to memory===
                            type = 'event'
                            created = self.curr_time
                            wait_time = int((self.curr_time - self.mobility_events[persona_name]['start_time']).total_seconds() / 60)
                            if wait_time >= 5:  # if wait for more than 5 minutes, add to memory
                                start_time_str = self.mobility_events[persona_name]['start_time'].strftime("%a %Y-%m-%d %H:%M")
                                content = f"{persona_name} waits at {link_name}; start time is {start_time_str}; wait time is {wait_time} minutes"
                                keywords = ["wait", link_name]
                                spatial_scope = link_name
                                time_scope = [self.mobility_events[persona_name]['start_time'].time(), self.curr_time.time()]
                                importance = generate_importance_score(persona, self.maze, "event", content)
                                node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
                                persona.lt_mem.add_concept_node(node)
                                                    
                            # Update mobility event and persona state
                            persona.st_mem.curr_place = link_name
                            persona.st_mem.curr_status = f"{persona_name} on the trip from {persona.st_mem.trip_start_facility} to {persona.st_mem.activity_facility}; trip trajectory: {persona.st_mem.trip_trajectory}; after waiting for {wait_time} minutes, currently riding on {link_name}; planned path left: {persona.st_mem.planned_path};"
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


    def _teleport_home(self, persona):
        persona_name = persona.st_mem.name
        # Store current location for cleanup
        current_place = persona.st_mem.curr_place
        current_event = self.mobility_events[persona_name]
        
        # 1. Remove persona from all current network queues based on current location and status
        if current_place in self.maze.facilities_info:
            # Remove from facility queues
            if persona_name in self.maze.facilities_info[current_place].get('staying', []):
                self.maze.facilities_info[current_place]['staying'].remove(persona_name)
            if persona_name in self.maze.facilities_info[current_place].get('waiting', []):
                self.maze.facilities_info[current_place]['waiting'].remove(persona_name)
                
        elif current_place in self.maze.nodes_info:
            # Remove from node waiting queue
            if persona_name in self.maze.nodes_info[current_place].get('waiting', []):
                self.maze.nodes_info[current_place]['waiting'].remove(persona_name)
                
        elif current_place in self.maze.links_info:
            # Remove from link queues - need to determine direction
            link_data = self.maze.links_info[current_place]
            
            # Determine direction from mobility event
            next_node = current_event.get('next_node')
            if next_node:
                endpoints = link_data['endpoints']
                direction = 1 if next_node == endpoints[0] else 0
            else:
                # If no next_node, check both directions
                direction = None
            
            # Remove from appropriate link queues based on current status
            if current_event['status'] == 'driving':
                if direction is not None:
                    if persona_name in link_data['driving'][direction]:
                        link_data['driving'][direction].remove(persona_name)
                else:
                    # Check both directions
                    for d in [0, 1]:
                        if persona_name in link_data['driving'][d]:
                            link_data['driving'][d].remove(persona_name)
                            
            elif current_event['status'] == 'walking':
                if direction is not None:
                    if persona_name in link_data['walking'][direction]:
                        link_data['walking'][direction].remove(persona_name)
                else:
                    for d in [0, 1]:
                        if persona_name in link_data['walking'][d]:
                            link_data['walking'][d].remove(persona_name)
                            
            elif current_event['status'] == 'riding':
                if direction is not None:
                    if persona_name in link_data['riding'][direction]:
                        link_data['riding'][direction].remove(persona_name)
                else:
                    for d in [0, 1]:
                        if persona_name in link_data['riding'][d]:
                            link_data['riding'][d].remove(persona_name)
                            
            elif current_event['status'] == 'waiting':
                if direction is not None:
                    if persona_name in link_data['waiting'][direction]:
                        link_data['waiting'][direction].remove(persona_name)
                else:
                    for d in [0, 1]:
                        if persona_name in link_data['waiting'][d]:
                            link_data['waiting'][d].remove(persona_name)
        
        # 2. Update persona state
        persona.st_mem.activity_facility = persona.st_mem.home_facility
        persona.st_mem.activity_index = -1
        persona.st_mem.activity_duration = timedelta(hours=8)
        persona.st_mem.reflect_every = None
        persona.st_mem.planned_path = []
        persona.st_mem.curr_place = persona.st_mem.home_facility
        persona.st_mem.curr_status = "Staying at home"
        persona.st_mem.trip_start_facility = None
        persona.st_mem.trip_trajectory = []
        
        # 3. Add persona to home facility staying queue
        home_facility = persona.st_mem.home_facility
        if 'staying' not in self.maze.facilities_info[home_facility]:
            self.maze.facilities_info[home_facility]['staying'] = []
        if persona_name not in self.maze.facilities_info[home_facility]['staying']:
            self.maze.facilities_info[home_facility]['staying'].append(persona_name)
        
        # 4. Update mobility events
        self.mobility_events[persona_name] = {
            'name': persona_name,
            'place': home_facility,
            'next_node': None,
            'status': 'staying',
            'start_time': self.curr_time,
            'description': 'staying at home (failsafe teleport)',
            'moved': False
        }
        
        # Update coordinates of the event
        coord = self.maze.get_coordinates(self.mobility_events[persona_name], self.curr_time)
        self.mobility_events[persona_name]['coord'] = coord
        
        # 5. Update cache file for frontend visualization
        json_path = 'gatsim/cache/curr_movements.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['mobility_events'][persona_name] = {
            'name': persona_name,
            'place': home_facility,
            'next_node': None,
            'status': 'staying',
            'start_time': self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
            'description': 'staying at home (failsafe teleport)',
            'moved': False,
            'coord': coord
        }
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        # 6. Add failsafe experience to persona's memory
        type_val = "event"
        created = self.curr_time
        content = f"{persona_name} failed to return home by end of day and was teleported home from {current_place}. This suggests poor time management or unexpected delays!"
        keywords = ["failsafe", "teleport", "time management", "end of day"]
        spatial_scope = None
        time_scope = None
        importance = generate_importance_score(persona, self.maze, "event", content)
        node = ConceptNode(type_val, created, content, keywords, spatial_scope, time_scope, importance)
        persona.lt_mem.add_concept_node(node)
            
        pretty_print(f"Failsafe completed: {persona_name} teleported from {current_place} to {home_facility}", 1)


    def _reset_state(self):
        """
        Step 3.4: Update network and facility states for personas to perceive
        - Reset all persona moved flags for next run step
        """                
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
            # Note: if agent is waiting at transit stop, they may wait for a long time
            # to save time, we only allow them to update their plan for every 10 minutes.
            wait_time = int((self.curr_time - event['start_time']).total_seconds() / 60 - 1)
            if wait_time % 10 == 0:
                return True
        elif event['status'] == "staying" and event['place'] in self.maze.facilities_info:
            # 2. If the current activity just finished, and departure time for next activity is due
            # Note: 'planned_duration' = None means leave upon arrival, say drop off kids, buy a coffee, etc.
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
            # 4. Staying at another facility
            if event['place'] != persona.st_mem.activity_facility:
                # if the persona is staying at a facility that is NOT the planned activity,
                # (this is a rare case, but indeed can happen)
                # reflect every 5 minutes to decide what to do next
                duration_int = int(duration.total_seconds() / 60)  # in minutes
                if duration_int % 5 == 0:
                    return True        

        # By default, don't make a new decision
        return False
        

    def _check_path(self):
        """ 
        If a agent is traveling, check if it has a valid path; so that it can reached its destination.
        Failsafe method.
        """
        for persona_name, persona in self.population.items():
            # if traveling, not arriving immediately (last link popped to mobility_events)
            if persona.st_mem.curr_place != persona.st_mem.activity_facility \
                and persona.st_mem.curr_place != self.maze.facility2node[persona.st_mem.activity_facility] \
                    and self.mobility_events[persona_name]['next_node'] != self.maze.facility2node[persona.st_mem.activity_facility]:
                # if no valid path found
                if persona.st_mem.planned_path is None or persona.st_mem.planned_path == []:
                    pretty_print(f"{persona.name} - no valid path found, using default path", 1)
                    start_node = persona.st_mem.curr_place
                    if persona.st_mem.curr_place in self.maze.links_info:
                        start_node = self.mobility_events['persona_name']['next_node']
                    persona.st_mem.planned_path = self.maze.get_shortest_path(start_node, persona.st_mem.activity_facility, persona.st_mem.travel_mode)['original_path']
                    
            
        
        
        
        

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
        simulation_folder = f"{config.simulation_storage}/{self.simulation_name}"

        while True: 
            sim_command = input("\nEnter option: (e.g. 'run 1 day', 'run 8 hours'; default: 'run 1 day')\n")
            sim_command = sim_command.lower().strip()
            
            if not sim_command: 
                sim_command = "run 1 day"  # default to run 1 day

            pretty_print(f">>> Run simulation for command: {sim_command}...", 0)
            
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
                break  # if you want to run multiple commands for a simulation, then remove this break
                
            elif ("call -- analysis" in sim_command.lower()): 
                # Starts a stateless chat session with the agent. It does not save 
                # anything to the agent's memory. 
                # Ex: call -- analysis Isabella Rodriguez
                persona_name = sim_command[len("call -- analysis"):].strip() 
                self.population[persona_name].user_converse_with_persona("analysis")


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
        simulation_folder = f"{config.simulation_storage}/{self.simulation_name}"

        while True: 
            #sim_command = input("\nEnter option: (e.g. 'run 1 day', 'run 8 hours'; default: 'run 1 day')\n")
            sim_command = sim_command.lower().strip()
            
            if not sim_command: 
                sim_command = "run 1 day"  # default to run 1 day

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
                break

            elif sim_command[:3] == "run":
                # Runs the number of steps specified in the prompt.
                num_minutes = parse_command(sim_command)
                num_steps = int(num_minutes / config.minutes_per_step)
                pretty_print(f">>> Start running for {num_minutes} minutes ({num_steps} steps).")
                self.start_server(num_steps)
                break
                
            elif ("call -- analysis" in sim_command.lower()): 
                # Starts a stateless chat session with the agent. It does not save 
                # anything to the agent's memory. 
                # Ex: call -- analysis Isabella Rodriguez
                persona_name = sim_command[len("call -- analysis"):].strip() 
                self.population[persona_name].user_converse_with_persona("analysis")
                break


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
        
    default_fork = "none"  #"base_the_town"
    #fork_name = input(f"Enter the name of the forked simulation: (default: {default_fork}); type 'none' for creating a new simulation\n").strip()
    if not fork_name:  # If user just presses Enter (empty string)
        fork_name = default_fork  # Set to default value
    if "none" in fork_name.lower():
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
    pretty_print()
    
    # Print initial state
    pretty_print("\nInitial State:", 1)
    for persona_name in persona_names:
        home_facility = backend.population[persona_name].st_mem.curr_place
        pretty_print(f"{persona_name} is at {home_facility}", 2)
    pretty_print()
    
    # run simulation
    backend.open_server_with_command(command)

        


def test():
    # For testing purposes
    # test creating new simulation
    #rs = BackendServer(None, "base_the_town")
    # test forking simulation
    #rs = BackendServer("base_the_town", "test")
    
    default_fork = "none" # "base_the_town"
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
    pretty_print()
    
    # Print initial state
    pretty_print("\nInitial State:", 1)
    for persona_name in persona_names:
        home_facility = backend.population[persona_name].st_mem.curr_place
        pretty_print(f"{persona_name} is at {home_facility}", 2)
    pretty_print()
    
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