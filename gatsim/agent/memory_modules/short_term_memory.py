"""
File: short_term_memory.py
Description: Defines the short-term memory module for generative agents.
**Short term memory is a dict**


# Introduction
The ShortTermMemory class in the provided code defines the short-term memory module for a generative agent. 
This class is responsible for tracking the agent’s current state, identity, planning, and reflection. 
It contains many attributes related to the agent’s activities, goals, interactions, and other personal information.
Short memory includes:
    1.	Core Identity of the Persona:
    •	The agent’s identity is defined by attributes like name, first_name, last_name, age, and other traits (e.g., innate, learned, currently, lifestyle, living_area).
    •	These attributes define who the persona is and what their context is within the world.
 
    2.	Persona activity plan:
    •	The agent has a daily activity plan that represent the tasks it aims to complete. These are stored in original_plans.
 
    5.	Persona Current Activity:
    •	The ShortTermMemory class also stores the agent’s current activity and its details (e.g., activity_facility, activity_duration, activity_description, etc.).
    •	The agent’s movement is managed by storing a planned paths (planned_path), representing the path the agent will move along with


# Examples
 - Original plans example:
    "original_plans": [
        {
            "reflection": "The past week was relatively calm, with a consistent routine of taking the metro to work and spending evenings at home. I enjoyed some photography during the weekend but haven't exercised much. This week, I look forward to maintaining my routine while incorporating more physical activity. The upcoming art exhibition at the Museum seems interesting, and I might visit it during lunch. I also need to ensure Sophia has the car for grocery shopping later today. Traffic in the afternoon can be congested, so I should plan my trips accordingly.",
            "plan": [
                ["Uptown apartment", "06:30", "none", "none", "none", "Wake up at home, complete morning routine."],
                ...],
            "concepts": [
                ["Museum hosts an art exhibition from 12:00 to 16:00", "Museum, art exhibition, noon", "Museum", "12:00-16:00"],
                ...],
            "datetime": "2025-03-10 00:00:00"
        }
    ]
    
 - Revised plans example:
    "revised_plans": [
        {
            "reflection": "The wildfire at the Amusement park has made St_5 unsafe for travel during 12:00-16:00. This might affect my return trip from the Museum if I take a path involving St_5. However, since I plan to use transit, this shouldn't directly impact me. Sophia confirmed she will meet Isabella at the Museum as planned, so my lunch break activity remains unchanged. Afternoon traffic near Supermarket and Food court is often congested, which may delay my return to the Office or later trips. I should monitor traffic conditions before departing the Museum.",
            "plan": [
                ["Museum", "12:30", 60, "transit", "shortest", "Visit the art exhibition at Museum during lunch break."],
                ...],
            "concepts": [
                [ "Amusement park wildfire makes St_5 unsafe during 12:00-16:00", "Amusement park, wildfire, St_5, unsafe, 12:00-16:00", "Amusement park, St_5", "12:00-16:00"],
                [ "Afternoon traffic near Supermarket and Food court tends to be congested", "Supermarket, Food court, congested, afternoon", "Supermarket, Food court", "17:00-18:00"]
                ...],
            "datetime": "2025-03-10 12:28:00"
        }
    ]
    
 - Plan revision description example:
"Time: 12:28
Reflections: 
The wildfire at the Amusement park has made St_5 unsafe for travel during 12:00-16:00. This might affect my return trip from the Museum if I take a path involving St_5. However, since I plan to use transit, this shouldn't directly impact me. Sophia confirmed she will meet Isabella at the Museum as planned, so my lunch break activity remains unchanged. Afternoon traffic near Supermarket and Food court is often congested, which may delay my return to the Office or later trips. I should monitor traffic conditions before departing the Museum.
Plan revisions: Daniel Nguyen - future plan updated to:
[['Museum', '12:30', 60, 'transit', 'shortest', 'Visit the art exhibition at Museum during lunch break.'], ['Office', '13:30', 120, 'transit', 'shortest', 'Return to Office and continue working after the exhibition.'], ['Gym', '17:30', 60, 'transit', 'shortest', 'Go to Gym for exercise before heading home.'], ['Uptown apartment', '19:00', 'none', 'transit', 'shortest', 'Head back home to Uptown apartment for dinner and relaxation.']] 

Time: 18:22
Reflections: 
The day has been going smoothly so far. I visited the Museum during lunch as planned, and traffic conditions have been stable. Sophia has already stopped by the Supermarket for groceries, so I don't need to worry about her needing the car anymore. However, my current trip to the Gym might take longer than expected due to a wait at Metro_2_link_5. I should consider whether to adjust my departure time or find an alternative path.
Plan revisions: Daniel Nguyen - next activity to Uptown apartment departure time updated to 18:40"

 - Daily reflections example:
    "daily_reflections": [
        {
            "reflection": "Today's activities went mostly as planned, but there were a few notable events. The wildfire at the Amusement park disrupted traffic along St_5 during the afternoon, though it didn't directly impact my transit route. However, I encountered a delay at Metro_2_link_5 on my way to the Gym, which slightly affected my schedule. In the future, I should consider adjusting departure times or exploring alternative routes during peak hours or when unexpected events occur.",
            "concepts": [
                ["Wildfire at Amusement park disrupts St_5 travel during 12:00-16:00", "Amusement park, wildfire, St_5, disruption", "Amusement park, St_5", "12:00-16:00"],
                ...],
            "datetime": "2025-03-10 23:59:00"
        }
    ]
"""
import os
import copy
from datetime import datetime, timedelta
import json
from gatsim import config
from gatsim import utils


class ShortTermMemory: 
    def __init__(self, persona_folder, **kwargs):
        """ 
        Initialize a new short term memory
        
        Args:
            persona_name (str): name of the persona
            persona_folder (str): path to the folder where the persona data is stored
            **kwargs (dict): dictionary of persona identity information;
        """
        # Persona identity
        self.persona_folder = persona_folder
        self.name = kwargs.get('name', None)
        self.age = kwargs.get('age', None)
        self.gender = kwargs.get("gender", None)
        self.highest_level_of_education = kwargs.get("highest_level_of_education", None)
        self.family_role = kwargs.get("family_role", None)
        self.licensed_driver = kwargs.get("licensed_driver", None)
        self.work_facility = kwargs.get("work_facility", None)
        self.work_time = kwargs.get("work_time", None)
        self.occupation = kwargs.get("occupation", None)
        self.preferences_in_transportation = kwargs.get("preferences_in_transportation", None)
        self.innate = kwargs.get("innate", None)
        self.lifestyle = kwargs.get("lifestyle", None)
        self.home_facility = kwargs.get("home_facility", None)
        self.household_size = kwargs.get("household_size", None)
        self.other_family_members = kwargs.get("other_family_members", None)
        self.number_of_vehicles_in_family = kwargs.get("number_of_vehicles_in_family", None)
        self.household_income = kwargs.get("household_income", None)
        self.friends = kwargs.get("friends", None)
        self.other_description = kwargs.get("other_description", None)

        # Simulation
        self.curr_time = datetime.strptime(kwargs.get("curr_time", config.start_date), "%Y-%m-%d %H:%M:%S")
        #self.importance_trigger_max = config.importance_trigger_max
        #self.importance_trigger_curr = self.importance_trigger_max
        #self.importance_ele_n = 0 
        #self.thought_count = 5
        
        # Persona plan
        self.original_plans = kwargs.get("original_plans", [])  # persona original plans (a list; one element for each day); self.original_plans[i] is a dict with keys "datetime", "reflection", "plan"; one for each day;
        self.revised_plans = kwargs.get("revised_plans", [])  # self.revised_plans[i] is a dict with keys "datetime", "reflection" and "plan"; one for each revision that happened today;
        self.daily_reflections = kwargs.get("daily_reflections", [])  # reflection on daily events; self.daily_reflections[i] is a dict with keys "datetime", "reflection"
        self.plan_revision_description = kwargs.get("plan_revision_description", "")  
        # It's a string summarizing the plan revisions made TODAY
        # This will be used to pass as context for decision!
            
        # Current activity
        # Note: 
        # 1) a activity plan is of list of activity which is a list of the following format:
        # [<activity_facility>, <activity_departure_time>, <travel_mode>, <reflect_every>, <activity_description>, <path>]
        # 2) current activity plan is part of self.original_plans[-1] if self.revised_plans is an empty list, namely for today no revision happens yet
        # otherwise, current activity plan is part of self.revised_plans[-1]
        # 3) these activity are updated when a persona
        #   i) finishes an activity or 
        #   ii) revises the plan or 
        #   iii) starts a new day
        self.activity_index = kwargs.get("activity_index", 0)  # (int) the index of current activity in the current plan (self.original_plans[-1] or self.revised_plans[-1])
        self.activity_facility = kwargs.get("activity_facility", kwargs.get('home_facility', None))  # (str) default to home_facility
        # <start_time> is a python datetime instance that indicates when the action has started. 
        self.activity_departure_time = kwargs.get("activity_departure_time", None)  # (datetime)
        # activity_duration is the integer value that indicates the number of minutes an action is meant to last. 
        # activity_duration is computed as the difference between the departure time of next activity and current activity
        self.activity_duration = kwargs.get("activity_duration", None)  # (timedelta); timedelta objects; None means depart right after arrival at the facility, like dropping off child at school, buy a coffee
        # <description> is a string description of the action. 
        self.travel_mode = kwargs.get("travel_mode", None)  # "drive" or "transit"; travel model that the persona use for this activity
        self.reflect_every = None  # (timedelta) how often should do persona can check to revise the activity plan; None means reflection only happens when activity duration is reached.
        self.activity_description = kwargs.get("activity_description", None)
        
        # Movements
        # Note: movements variables are updated by simulator backend
        self.planned_path = kwargs.get("planned_path", [])
        # planned path is a list of tuples:
        # [(next_link, next_mode, next_node), ...]
        # next_mode = "drive"/'walk'/'ride'
        # first element's next_link must have current node as a endpoint
        self.curr_place = kwargs.get("curr_place", self.home_facility)  # (str) current place in the network; node or link or facility
        self.curr_status = kwargs.get("curr_status", None)  # (str) description of what the persona is doing now (say, waiting on link, staying in a facility ...)        
        self.trip_start_facility = kwargs.get("trip_start_facility", None)  # to record the start facility of the trip; this is needed since activity_facility is the target; we need another variable to store the source (namely the previous target); updated by backendserver
        self.trip_trajectory = kwargs.get("trip_trajectory", [])  # record the persona travel trajectory; updated by backendserver

    
    def load(self, persona_folder=None):
        """ 
        Load persona's short term memory.
        
        Args: 
            st_mem_path: The file where we will be loading our persona's state. 
            
        Returns:: 
            a Persona object.
        """
        if persona_folder is None:
            persona_folder = self.persona_folder
        
        memory_path = os.path.join(persona_folder, "short_term_memory.json")
        if not os.path.exists(memory_path):
            return  # No memory file exists yet
        
        kwargs = json.load(open(memory_path))
        # load instance variables
        # identity
        self.name = kwargs.get('name', None)
        self.age = kwargs.get('age', None)
        self.gender = kwargs.get("gender", None)
        self.highest_level_of_education = kwargs.get("highest_level_of_education", None)
        self.family_role = kwargs.get("family_role", None)
        self.licensed_driver = kwargs.get("licensed_driver", None)
        self.work_facility = kwargs.get("work_facility", None)
        self.work_time = kwargs.get("work_time", None)
        self.occupation = kwargs.get("occupation", None)
        self.preferences_in_transportation = kwargs.get("preferences_in_transportation", None)
        self.innate = kwargs.get("innate", None)
        self.lifestyle = kwargs.get("lifestyle", None)
        self.home_facility = kwargs.get("home_facility", None)
        self.household_size = kwargs.get("household_size", None)
        self.other_family_members = kwargs.get("other_family_members", None)
        self.number_of_vehicles_in_family = kwargs.get("number_of_vehicles_in_family", None)
        self.household_income = kwargs.get("household_income", None)
        self.friends = kwargs.get("friends", None)
        self.other_description = kwargs.get("other_description", None)
        
        # simulation
        self.curr_time = datetime.strptime(kwargs.get("curr_time", config.start_date), "%Y-%m-%d %H:%M:%S")
        
        # Persona plan
        self.original_plans = kwargs.get("original_plans", [])  # persona original plans (a list; one element for each day); self.original_plans[i] is a dict with keys "datetime", "reflection", "plan"
        self.revised_plans = kwargs.get("revised_plans", [])  # self.revised_plans[i] is a dict with keys "datetime", "reflection" and "plan"
        self.plan_revision_description = kwargs.get("plan_revision_description", "")
        self.daily_reflections = kwargs.get("daily_reflections", [])  # reflection on daily events; self.daily_reflections[i] is a dict with keys "datetime", "reflection"
        # convert datetime strings to datetime objects
        for i, plan in enumerate(self.original_plans):
            self.original_plans[i]["datetime"] = datetime.strptime(plan["datetime"], "%Y-%m-%d %H:%M:%S")
        for i, plan in enumerate(self.revised_plans):
            self.revised_plans[i]["datetime"] = datetime.strptime(plan["datetime"], "%Y-%m-%d %H:%M:%S")
        for i, reflection in enumerate(self.daily_reflections):
            self.daily_reflections[i]["datetime"] = datetime.strptime(reflection["datetime"], "%Y-%m-%d %H:%M:%S")
        
        # current activity
        self.activity_index = kwargs.get("activity_index", 0)
        self.activity_facility = kwargs.get("activity_facility", kwargs['home_facility'])
        self.activity_departure_time = kwargs.get("activity_departure_time", None)
        if self.activity_departure_time:
            self.activity_departure_time = datetime.strptime(self.activity_departure_time,  "%Y-%m-%d %H:%M:%S")
        self.activity_duration = kwargs.get("activity_duration", None)
        if self.activity_duration:
            self.activity_duration = timedelta(minutes=self.activity_duration)
        self.travel_mode = kwargs.get('travel_mode', True)  # True if drive; False if walk or use transit
        self.reflect_every = kwargs.get('reflect_every', None)  # how often should we check whether persona want to continue to stay / wait at the facility
        if self.reflect_every:
            self.reflect_every = timedelta(minutes=self.reflect_every)
        self.activity_description = kwargs.get("activity_description", None)
        
        # movements
        self.planned_path = kwargs.get("planned_path", [])
        self.curr_place = kwargs.get("curr_place", self.home_facility)  # location is node or link on transport networks
        self.curr_status = kwargs.get("curr_status", None)  # description of what the persona is doing now (say, waiting on link, ...)  
        self.trip_start_facility = kwargs.get("trip_start_facility", None)
        self.trip_trajectory = kwargs.get("trip_trajectory", [])
    
    
    def save(self, persona_folder=None):
        """
        Save persona's st_mem. 

        Args: 
            out_json: The file where we wil be saving our persona's state. 
            
        Returns:: 
            None
        """
        if persona_folder is None:
            persona_folder = self.persona_folder
            
        out_json = self.persona_folder + "/short_term_memory.json"
        
        # some instance variables may include datetime object; convert to str for save
        original_plans_for_save = []
        for plan in self.original_plans:
            plan = copy.deepcopy(plan)
            plan['datetime'] = plan['datetime'].strftime("%Y-%m-%d %H:%M:%S")
            original_plans_for_save.append(plan)
        revised_plans_for_save = []
        for plan in self.revised_plans:
            plan = copy.deepcopy(plan)
            plan['datetime'] = plan['datetime'].strftime("%Y-%m-%d %H:%M:%S")
            revised_plans_for_save.append(plan)
        daily_reflections_for_save = []
        for reflection in self.daily_reflections:
            reflection = copy.deepcopy(reflection)
            reflection['datetime'] = reflection['datetime'].strftime("%Y-%m-%d %H:%M:%S")
            daily_reflections_for_save.append(reflection)
            
        st_mem_for_save = {
            # identity
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'highest_level_of_education': self.highest_level_of_education,
            'family_role': self.family_role,
            "licensed_driver": self.licensed_driver,
            "work_facility": self.work_facility,
            "work_time": self.work_time,
            "occupation": self.occupation,
            "preferences_in_transportation": self.preferences_in_transportation,
            "innate": self.innate,
            "lifestyle": self.lifestyle, 
            "home_facility": self.home_facility,
            "household_size": self.household_size,
            "other_family_members": self.other_family_members,
            "number_of_vehicles_in_family": self.number_of_vehicles_in_family,
            "household_income": self.household_income,
            "friends": self.friends,
            "other_description": self.other_description,
            
            # simulation
            "curr_time": self.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
            
            # plan
            "original_plans": original_plans_for_save,
            "revised_plans": revised_plans_for_save,
            "daily_reflections": daily_reflections_for_save,
            "plan_revision_description": self.plan_revision_description,
            
            # current activity
            "activity_index": self.activity_index,
            "activity_facility": self.activity_facility,
            "activity_departure_time": self.activity_departure_time.strftime("%Y-%m-%d %H:%M:%S") if self.activity_departure_time  else None,
            "activity_duration": int(self.activity_duration.total_seconds() / 60) if self.activity_duration else None,  # convert to int (min)
            "travel_mode": self.travel_mode,
            "reflect_every": int(self.reflect_every.total_seconds() / 60) if self.reflect_every else None,  # convert to int (min)
            "activity_description": self.activity_description,
            
            # movements
            "planned_path": self.planned_path,
            "curr_place": self.curr_place,
            "curr_status": self.curr_status,
            "trip_start_facility": self.trip_start_facility,
            "trip_trajectory": self.trip_trajectory
        }
        
        with open(out_json, "w") as outfile:
            json.dump(st_mem_for_save, outfile, indent=4) 


    def get_str_persona_identity(self): 
        """
        This describes the persona_identity summary of this persona -- basically, the bare minimum description of the persona
        that gets used in almost all prompts that need to call on the persona. 

        Args:
            None
            
        Returns:
            the identity summary of the persona in a string form.
        """
        persona_identity = f"""Person identity description:
-----PERSON IDENTITY SECTION START-----
Name: {self.name}
Age: {self.age}
Gender: {self.gender}
Highest level of education: {self.highest_level_of_education}
Family role: {self.family_role}
Licensed driver: {self.licensed_driver}
Work place: {self.work_facility}
Work time: {self.work_time}
Occupation: {self.occupation}
Preferences for transportation: {self.preferences_in_transportation}
Innate traits: {self.innate}
Life style: {self.lifestyle}
Home place: {self.home_facility}
Household size: {self.household_size}
Other family members: {self.other_family_members}
Number of vehicles of the family: {self.number_of_vehicles_in_family}
Household income: {self.household_income}
Friends: {self.friends}
Other description of this person: {self.other_description}
-----PERSON IDENTITY SECTION END-----"""
        return persona_identity



    def get_str_revised_plans(self):
        ans = f"""
The person may have revised activity plan for today. Revisions as well as reflections are listed below (empty if no revision has happened yet):
---TODAY ACTIVITY PLAN REVISIONS SECTION START---{self.plan_revision_description}---TODAY ACTIVITY PLAN REVISIONS SECTION END---""" 
        return ans  
    
    
    if False:
        # alternative: build from list of revised plans
        def get_str_revised_plans(self):
            ans = f"""
    The person has revised activity plan for today. Revisions as well as reflections are listed below (empty if no revision has happened yet):
    -----TODAY ACTIVITY PLAN REVISIONS SECTION START-----"""     

            num_revisions = len(self.revised_plans)
            if num_revisions > 1:
                ans += "\nPrevious revised plans (outdated)"
                
            for i in range(num_revisions):
                if i == num_revisions - 1:
                    # for the latest plan, add this
                    ans += "\nLast revised plan:"
                    
                ans += f"""
    Revision time: {self.revised_plans[i]['datetime'].strftime("%H:%M")}

    Reflection: {self.revised_plans[i]['reflection']}

    Revised plan:
    {self.revised_plans[i]['plan']}"""

            ans +="""
    -----TODAY ACTIVITY PLAN REVISIONS SECTION END-----""" 
            return ans    


    def get_str_last_original_plan(self, new_day):            
        """ 
        Get the description of the latest original plan.
        If called on the start of the day, it would be last days original plan;
        if called during the day, it would be the today's original plan.
        """
        # check whether it's new day
        #new_day = False
        #last_time = self.curr_time - timedelta(minutes=config.minutes_per_step)
        #if self.curr_time.day != last_time.day:
        #    new_day = True
            
        if new_day:
            ans = f"""
The original activity plan and reflection of {self.name} at the start of previous day (empty if now it's the first day of simulation):
---YESTERDAY ORIGINAL ACTIVITY PLAN SECTION START---"""
        else:
            ans = f"""
The original activity plan and reflection of {self.name} at the start of today:
---TODAY ORIGINAL ACTIVITY PLAN SECTION START---"""
            
        if len(self.original_plans) > 0:
            ans +=f"""
Reflection: 
{self.original_plans[-1]['reflection']}

Original daily activity plan:
{self.original_plans[-1]['plan']}"""

        if new_day:
            ans += """\n---YESTERDAY ORIGINAL ACTIVITY PLAN SECTION END---""" 
        else:
            ans += """\n---TODAY ORIGINAL ACTIVITY PLAN SECTION END---""" 
        
        return ans

    def get_str_last_daily_reflection(self):
        """ 
        Get the latest daily reflection at night; 
        Note: it's last day's reflection.
        """
        ans = """
Daily summary of previous day's experiences (empty if now it's the first day of simulation):
---YESTERDAY DAILY SUMMARY SECTION START---\n"""

        if len(self.daily_reflections) > 0:
            ans += f"Reflection: {self.daily_reflections[-1]['reflection']}"
            
        ans += """\n---YESTERDAY DAILY SUMMARY SECTION END---"""
        return ans


    def get_str_current_activity_and_status(self):
        """ 
        Get the string description of the current activity and mobility status.
        """
        ans = f"""
Description of {self.name} current activity and person mobility status:
---CURRENT ENGAGED ACTIVITY STATUS SECTION START---
Current time: {self.curr_time}
Activity facility: {self.activity_facility}
Activity description: {self.activity_description}
Activity departure time: {self.activity_departure_time}
Activity planned duration: {self.activity_duration}
Reflection interval: {self.reflect_every}
Travel mode: {self.travel_mode}
Trip trajectory: {self.trip_trajectory}
Current place: {self.curr_place}
Planned path left: {self.planned_path}
Current mobility status: {self.curr_status}
---CURRENT ENGAGED ACTIVITY STATUS SECTION END---"""
        return ans


if __name__ == "__main__":
    persona_name = "Isabella Rodriguez"
    persona_folder = "gatsim/storage/base_the_town/personas/Isabella Rodriguez"
    population_info = json.load(open(f"{config.agent_path}/population_info.json"))
    kwargs = population_info[persona_name]
    #kwargs['name'] = persona_name

    st_mem = ShortTermMemory(persona_folder, **kwargs)
    st_mem.save()