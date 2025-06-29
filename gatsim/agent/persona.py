"""
File: persona.py
Description: Defines the Persona class that powers the agents. 

# Persona properties:
Personal attributes:
 - name (str)
 - gender (str: 'male'/'female')
 - age (int)
 - highest_level_of_education
 - family_role (str: 'father'/'mother'/'son'/'daughter'/'single')
 - licensed_driver (Bool)
 - work_facility (str: 'School'/'Museum'/'Hospital'/'Cinema'/'Supermarket'/'Food court'/'Amusement park'/'Coffee shop'/'Factory'/'Office'/'Gym')
 - occupation (str)
 - preferences_in_transportation (str)
 - innate (str)
 - lifestyle (str)
Household attributes
 - home_facility (str: 'Uptown apartment'/'Midtown apartment')
 - household_size (int)
 - other_family_members (a list of names)
 - number_of_vehicles_in_family (int)
 - household_income (str: "high", "middle", "low")
Social attributes
 - friends (list of names)
Additional
 - other_description (str)

Examples:
population_info['Isabella Rodriguez'] = {
 'name': 'Isabella Rodriguez',
 'gender': 'female',
 'age': 34,
 'highest_level_of_education': 'master',
 'family_role': 'single',
 'licensed_driver': True,
 'work_facility': 'Coffee shop',
 'occupation': 'barista',
 'preferences_in_transportation': 'prefer to travel alone and prefer safer way to travel; mainly drive around', 
 'innate': "friendly, outgoing, hospitable",
 'lifestyle': "Isabella Rodriguez goes to bed around 11pm, awakes up around 6am.",
 'home_facility': 'Uptown apartment',
 'household_size': 1,
 'other_family_members': [],
 'number of vehicles': 1,
 'household_income': 'medium',
 'friends': ['Jennifer Moore'],
 'other_description': 'Isabella Rodriguez is a cafe owner who loves to make people feel welcome. She is always looking for ways to make the cafe a place where people can come to relax and enjoy themselves.',
}


# The main cognition sequence:
    perceive -> retrieve -> reflect & plan -> execute
 
 -	Perceive the environment: get the events that are happening around the persona, and what activity his or her family members and friends are engaged in.
 -	Retrieve relevant memories: use the retrieve function to get relevant memories from self.lt_mem.
 - Reflect on experiences: reflect on past experiences, perceived events, retrieved memories.
 - Plan the activities: based on the reflection, determined whether the plan need to be updated; if so, update the activity plan for the rest of the day.
 -	Execute the plan.
"""
import os
import json
from datetime import datetime, timedelta
from gatsim import config
from gatsim.utils import convert_time_str_to_datetime, pretty_print
from gatsim.agent.memory_modules.short_term_memory import ShortTermMemory
from gatsim.agent.memory_modules.long_term_memory import LongTermMemory
from gatsim.agent.cognitive_modules.perceive import perceive
from gatsim.agent.cognitive_modules.plan import (generate_daily_activity_plan,
                                                 update_daily_activity_plan)
from gatsim.agent.cognitive_modules.reflect import reflection_trigger, daily_reflection

class Persona: 
    """ Persona class: represents a single agent in the simulation. 
    The code sets up the agent’s memories (short-term, long-term) and provides methods for cognitive processes 
    like perceiving, retrieving, planning, reflecting, and executing actions.
    """
    def __init__(self, persona_name, persona_folder, **persona_identity):
        self.name = persona_name  # <name> is the full name of the persona. This is a unique identifier for the persona.
        self.persona_folder = persona_folder
        if not os.path.exists(persona_folder):
            os.makedirs(persona_folder)
        self.st_mem = ShortTermMemory(persona_folder, **persona_identity)
        self.lt_mem = LongTermMemory(persona_folder)        
        
    def load(self, persona_folder=None):
        if not persona_folder:
            persona_folder = self.persona_folder
        self.st_mem.load(persona_folder)
        self.lt_mem.load(persona_folder)

    def save(self, persona_folder=None): 
        """
        Save persona's current state (i.e., memory). 
        Saved in persona_folder. No need to pass persona_folder since it's recorded when persona is created.
        """
        self.lt_mem.save(persona_folder)
        self.st_mem.save(persona_folder)


    def update_activity(self, maze, next_node=None):
        """ 
        When current activity reached its ending time, or agent changed mind and want to pass to next activity, update it.
        
        Args:
            maze (Maze): Maze class object of the world.
            next_node (str): next node to go to; if ongoing activity is interrupted, next_node is the node where the agent is going to.
        """
        current_plan = self.st_mem.revised_plans[-1]['plan'] if self.st_mem.revised_plans else self.st_mem.original_plans[-1]['plan']
        self.st_mem.activity_index += 1
        next_activity = current_plan[self.st_mem.activity_index]
        # Each activity is a list of 6 elements:
        #       0                       1                       2               3           4               5
        #[<activity_facility>, <activity_departure_time>, <reflect_every>, <travel_mode>, <path>, <activity_description>]
        self.st_mem.activity_facility = next_activity[0]
        self.st_mem.activity_departure_time = self.st_mem.curr_time  # next activity must start from now
        # activity duration (timedelta)
        if self.st_mem.activity_index < (len(current_plan) - 1):
            # if next activity is not last activity
            next_next_activity_departure_time = current_plan[self.st_mem.activity_index + 1][1]
            if next_next_activity_departure_time != 'none':
                next_next_activity_departure_time = convert_time_str_to_datetime(self.st_mem.curr_time, next_next_activity_departure_time)
                self.st_mem.activity_duration = next_next_activity_departure_time - self.st_mem.curr_time
            else:
                # if next_next_activity_departure_time is 'none', it means that next next activity starts right upon the persona arriving at the facility of next_activity
                # in this case set st_mem.activity_duration to be None
                # In simulation backend, we will detect whether "planned_duration == None" to decide whether the activity is completed
                self.st_mem.activity_duration = None  # leave immediately after arriving at the facility of next_activity
        else:
            # if next activity is the last going back home activity, set duration to be long enough
            # note that new plan wil be made and activities will be updated at the start of next (new) day
            self.st_mem.activity_duration = timedelta(hours=24)
        # reflect every
        reflect_every = next_activity[2]
        if reflect_every == 'none':
            # if the reflect_every is 'none', then set reflect_every to be None; which means the activity should not be interrupted
            self.st_mem.reflect_every = None
        else:
            if isinstance(reflect_every, str):
                reflect_every = int(reflect_every)
            self.st_mem.reflect_every = timedelta(minutes=reflect_every)
            if self.st_mem.activity_facility == self.st_mem.work_facility:
                # if the activity is working, then reflect_every should be at least config.min_work_reflect_every
                self.st_mem.reflect_every = max(self.st_mem.reflect_every, timedelta(minutes=config.min_work_reflect_every))
            else:
                # if not working, then reflect_every should be at least config.min_reflect_every
                self.st_mem.reflect_every = max(self.st_mem.reflect_every, timedelta(minutes=config.min_reflect_every))
        # travel mode
        self.st_mem.travel_mode = next_activity[3]
        if self.st_mem.travel_mode not in ["drive", "transit", "none"]:
            pretty_print(f"{self.st_mem.name} has an invalid travel mode: {self.st_mem.travel_mode}", 2)
            # failsafe
            self.st_mem.travel_mode = "transit"
        # path
        path = next_activity[4]
        if path == "none":
            # say for waking up and doing morning routines activity, there is no need to travel.
            self.st_mem.planned_path = []
            # In case agent output "none" in a wrong way (failsafe)
            if not maze.same_node(self.st_mem.curr_place, self.st_mem.activity_facility):
                pretty_print(f"Error 001: {self.st_mem.name} current place: {self.st_mem.curr_place}; next activity: {next_activity[0]}; but path is none", 2)
                # failsafe
                path = "shortest"

        if path == "shortest":
            # if use realtime shortest path
            start_node = self.st_mem.curr_place
            if self.st_mem.curr_place in maze.links_info:
                if next_node != None:
                    start_node = next_node
                else:
                    raise ValueError(f"next_node not specified when curr_place is a link.")               
            self.st_mem.planned_path = maze.get_shortest_path(start_node, next_activity[0], travel_mode=self.st_mem.travel_mode)['original_path']
        elif path != "none":  # "none" case has been handled above
            # if persona specified a path
            roads = [k.strip() for k in next_activity[4].split(',')]
            start_node = self.st_mem.curr_place
            if self.st_mem.curr_place in maze.links_info:
                if next_node != None:
                    start_node = next_node
                else:
                    raise ValueError(f"next_node not specified when curr_place is a link.")
            self.st_mem.planned_path = maze.convert_path_format(start_node, next_activity[0], self.st_mem.travel_mode, roads)
            
        # activity description
        self.st_mem.activity_description = next_activity[5]
        
        # print
        pretty_print()
        pretty_print(f"{self.name} - current place: {self.st_mem.curr_place}; current activity updated to:", 2)
        pretty_print()
        pretty_print(f"activity_index: {self.st_mem.activity_index}", 2)
        pretty_print(f"activity_facility: {self.st_mem.activity_facility}", 2)
        pretty_print(f"activity_departure_time: {self.st_mem.activity_departure_time}", 2)
        pretty_print(f"activity_duration: {self.st_mem.activity_duration}", 2)
        pretty_print(f"reflect_every: {self.st_mem.reflect_every}", 2)
        pretty_print(f"travel_mode: {self.st_mem.travel_mode}", 2)
        pretty_print(f"planned_path: {self.st_mem.planned_path}", 2)
        pretty_print(f"activity_description: {self.st_mem.activity_description}", 2)
        
            
    def plan_for_test(self, maze, population):
        """
        Simplified test method for transport simulation that simulates person movement decisions.
        Personas will follow their existing plan until they reach their destination, then stay there.
        Do nothing.
        """            
        pass
        
    def plan(self, maze, population):
        """
        This is the main cognitive function where our main sequence is called. 

        Args: 
            maze (Maze): The Maze class of the current world. 
            population (dict): the population of the current world. A dict that map persona_name to Persona object.
            
        Returns: 
            None.
        
        Note: persona.st_mem and persona.lt_mem may be modified.
        """
        #===============================Decision making process===============================        
        # Step 0. detect if it’s a new day or end of day
        # We figure out whether the persona started a new day, and if it is a new
        # day, whether it is the very first day of the simulation. This is 
        # important because we set up the persona's long term plan at the start of
        # a new day. 
        new_day = False
        last_time = self.st_mem.curr_time - timedelta(minutes=config.minutes_per_step)
        if self.st_mem.curr_time.day != last_time.day:
            new_day = True
        
        # Step 1. Perceive the environment: get the events that are happening around the persona
        perceived, traffic_state = perceive(self, maze, population)  # Input maze and population to perceive
        # Note: perceived events are added to the short term memory.
        retrieved = self.lt_mem.retrieve(perceived, maze)
        # Note: retrieved are memories from self.lt_mem, excluding perceived.
        
        # Step 2. If it’s a new day, generate a original daily plan.
        if new_day:
            pretty_print()
            pretty_print(f"now {self.st_mem.name} generating new day activity plan", 2)
            generate_daily_activity_plan(self, maze, population, perceived, traffic_state, retrieved)
            # realtime traffic state not needed
            # but perceived is still needed for scheduled events like exhibition at Museum; they may affect daily activity plan
            # plan saved to self.st_mem.original_plans
            # self.lt_mem activity variables also updated
            
            # initialize plan revision list for persona for the new day
            self.st_mem.revised_plans = []  # initialize st_mem.revised_plans to be an empty list for today
            self.st_mem.plan_revision_description = ""  # initialize today's plan revision description to be an empty string
            
        # Step 3. During the day, if its time to decide, make a new plan (optional)
        else:
            pretty_print()
            pretty_print(f"now {self.st_mem.name} consider revising activity plan", 1)
            pretty_print()
            pretty_print(f"current condition:", 1)
            pretty_print(f"curr place: {self.st_mem.curr_place}", 1)
            pretty_print(f"activity index: {self.st_mem.activity_index}", 1)
            pretty_print(f"activity facility: {self.st_mem.activity_facility}", 1)
            pretty_print(f"activity departure time: {self.st_mem.activity_departure_time}", 1)
            pretty_print(f"activity duration: {self.st_mem.activity_duration}", 1)
            pretty_print(f"activity reflect every: {self.st_mem.reflect_every}", 1)
            pretty_print(f"activity travel mode: {self.st_mem.travel_mode}", 1)
            pretty_print(f"activity planned path: {self.st_mem.planned_path}", 1)
            pretty_print(f"activity description: {self.st_mem.activity_description}", 1)
            pretty_print()
            pretty_print(f"current plan:", 1)
            current_plan = self.st_mem.revised_plans[-1]['plan'] if self.st_mem.revised_plans else self.st_mem.original_plans[-1]['plan']
            pretty_print(current_plan, 1)
            pretty_print()
            # update plan
            update_daily_activity_plan(self, maze, population, perceived, traffic_state, retrieved)
            # new plan saved to self.st_mem.revised_plans
        #====================================================================================
                
    
    def daily_reflection(self, maze):
        """
        This function is called at the end of each day.
        
        Args:
            maze (Maze): The Maze class of the current world.
            
        Returns:
            None.
        """
        pretty_print()
        pretty_print(f"{self.name} - daily reflection", 1)
        daily_reflection(self, maze)


def initialize_population(population_info_file, simulation_folder):
    """ 
    Initialize population by a json file that contains personas' information.
    
    Args:
        population file path (json file with keys being names and values be dicts of attributes).
        
    Returns:
        A dict that map persona name to persona object.
    """
    population_info = json.load(open(population_info_file))
    population = dict()
    os.makedirs(f'{simulation_folder}/personas', exist_ok=True)
    for persona_name, kwargs in population_info.items():
        persona_folder = f"{simulation_folder}/personas/{persona_name}"
        persona = Persona(persona_name, persona_folder, **kwargs)
        persona.save()
        population[persona_name] = persona
    return population


def clean_up_memories(population):
    """
    clean up memories of all personas if necessary
    
    Args:
        population (dict): population of personas
    
    Outputs:
        None
    """
    for persona_name in population:
        persona = population[persona_name]
        persona.lt_mem.clean_up_memory()


if __name__ == '__main__':
    # test in population loading
    population = initialize_population(config.agent_path + '/population_info.json', 'gatsim/storage/base_the_town')
    pretty_print()
    