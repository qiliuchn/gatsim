"""
File: plan.py
Description: This defines the "Plan" module for generative agents. 

# Overall Flow：
 - On a new day start → agent need to reflect based on last day morning reflection and last daily reflection, generates a new day activity plan (generate_daily_activity_plan);
 It does not create ConceptNode; long term memory is not updated.
In short,  this is daily introspection method that updates the agent’s sense of self, emotional state, and activity plan for the new day, based on its memories and recent experiences.

 - During the day → persona follows the activity plan; persona may revise the plan when
     1) traveling to the activity facility, waiting at a node;
     2) staying at the facility, for reflect_every minutes;
     3) when an activity finishes
     
    The context provided is 
     1) perceived events
     2) retrieved memories
     3) realtime traffic state
     4) original plan
     5) plan revisions
     6) current condition
     
    Persona need to reflect using the information above and decides whether to:
     1) retain the latest activity plan; no changes;
     2) retain the latest activity plan, but reroute to realtime shortest path (calling maze's find shortest path function);
     3) retain the latest activity plan, but reroute to a give path (path provided);
     4) revise next activity departure time;
     5) revise the latest activity plan.
     
 - On the end of the day →  agent reflect on daily experiences.
 
 
# Variables
## Activity variables: The term “activity” in this case refers to a specific action or task that the persona is engaged in at any given moment. It's determined by the facility that it takes place.
- st_mem.activity_facility:
    •	Purpose: Represents the activity location (facility) where the action is taking place.
    •	Example: "Gym".

- st_mem.activity_departure_time:
    •	Purpose: The start time of the action, represented as a datetime object.
    •	Example: A time when the action begins, like "2025-03-31 08:00:00".

- st_mem.activity_duration:
    •	Purpose: The duration (in minutes) that the action is supposed to last.
    •	Example: 60 minutes (1 hour) for an action like “eating breakfast.”

- st_mem.activity_description:
    •	Purpose: A text description of the action being performed.
    •	Example: "doing yoga", "working on painting project". This is a human-readable summary of the action.

- st_mem.travel_mode:
    How to get to the activity facility. True if persona drive to the activity facility. False if persona walk or ride metro.

- st_mem.reflect_every:
    When a persona is engaged in an activity, reflect_every decides how often persona can revise the activity plan. 
    We don't want a persona to revise his or her plan for every minute. This is important for simulation efficiency.
        
## Movement variables:
- st_mem.planned_path:
	•	This variable stores a list of (next_link, next_mode, next_node) representing the path the persona will follow to complete their current action.


## Plan variables:
- st_mem.original_plans: original plan made at the beginning of the day; one for each day;
- st_mem.revised_plans: revised plans made during current day.

A plan is a list of activities.
Each activity is a list of 6 elements:
#       0                       1                       2               3           4               5
#[<activity_facility>, <activity_departure_time>, <reflect_every>, <travel_mode>, <path>, <activity_description>]

where
<activity_facility> is a string, which should be a valid facility name for the activity; it's the place where the activity takes place. For example, if the activity is about working, then it should be the working place; if the activity is about playing basketball, then it should be Gym, and so on.
<activity_departure_time> is a time string of the format "%H:%M" (e.g., "14:30"); it's the time when the person depart for <activity_facility>. For the first waking up routine activity, it means the wake-up time.
Departure time being "none" means the person will start this activity right after arriving at the previous activity facility; this is suitable for activities with uncertain departure time, like "driving to work" would happen right after "dropping off child at school", "heading to Office" happens right after "grab a coffee".
<reflect_every> is an int meaning how often the person is able to perceive surrounding events / family member and friends activities / current traffic condition in order to make revisions to the activity plan;
During the interval between decision time points, person should stay at the facility engaged in the current activity and no changes can be made to the plan;
Unit is minutes. It could be "none" if the activity is short enough or the person don't want the activity to be interrupted;
If a person at working place (say Office, Factory, manager or baker at Coffee shop, cinema manager at Cinema, etc.), then <reflect_every> should be at least 120 minutes or "none". 
For part time activities (like doing sports at Gym, watching film at Cinema, playing in Amusement Park, eating in Food court, etc.) <reflect_every> should be at least 60 minutes or 'none';
The first activity (waking up and doing morning routines) should have <reflect_every> to be "none" (don't interrupt the sleep);
The departing home activity (the second activity) should have <reflect_every> to be at least 20 minutes; namely check whether to depart home at most frequently for every 20 minutes;
If a person goes to Hospital for medical treatment, the <reflect_every> should be "none";
The last activity (going back to home and sleeping) should have <reflect_every> to be "none" (don't interrupt the sleep);
Persona will always to able to update plan when an activity is finished.
<travel_mode> is a string, "drive" or "transit"; if "drive", the person will drive to the activity's facility; if "transit", the person should walk or use transit to reach the activity facility;
<path> is a string describing the path info from last activity facility to current activity facility;
"none" if there is no need to travel (applicable only to the first morning routines activity);
"shortest" means that the person don't have preference over the path, then shortest path at departure time will be used (recommended for irregular activities like recreational activities);
If the person do want to specify the path; let path be a string of road or metro line names separated by comma (e.g. "Ave_1, Metro_2, Ave_3") (recommended for regular activities like going to and back from work place);
Road names should follow the traveling order from start to end;
Do NOT use link names for the path. Use road or metro line names like "Ave_1" or "Metro_2"! and do NOT repeat!
<activity_description> is a string, describing the content of the activity, like the people (e.g. family members, friends) involved in the activity.


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

import json
import re
from datetime import datetime, time, timedelta
from gatsim import config
from gatsim.utils import update_cache_concurrent_safe
from gatsim.utils import extract_json_from_string, convert_time_str_to_datetime, pretty_print
from gatsim.agent.llm_modules.llm import llm_generate, generate_prompt, llm_generate_with_json_extraction_and_retries
from gatsim.agent.llm_modules.run_prompt import generate_importance_score
from gatsim.agent.cognitive_modules.perceive import perceive
from gatsim.agent.memory_modules.long_term_memory import (convert_concept_nodes_to_str, 
                                                          convert_concept_tuple_to_concept_node,
                                                          ConceptNode)



def extract_path(plan):
    """ 
    extract path list from a plan string
    here a path is a list of road names
    
    Args:
        plan (str): a string of planed path
    Returns:
        roads: a list of road names; None if the plan is invalid
    """
    if ":" in plan:
        # example: "update path: St_3, Ave_3"
        roads = plan.split(':')[1].strip()
        roads = [k.strip() for k in roads.split(',')]
    elif "[" in plan and "]" in plan:
        # example: update current path to ['Ave_4', 'St_5', 'Ave_1']
        match = re.search(r"\[(.*?)\]", plan)
        items_str = match.group(1)
        # Split by comma, strip spaces and quotes
        roads = [item.strip().strip("'\"") for item in items_str.split(',')]
    else:
        # other cases:
        # example: update current path to 'Ave_4', 'St_5', 'Ave_1'
        # use LLM to extract the roads
        prompt_input = [plan]
        prompt_template = config.agent_path + "/llm_modules/prompt_templates/extract_path_info_v1.txt"
        prompt = generate_prompt(prompt_input, prompt_template)
        output= llm_generate_with_json_extraction_and_retries(prompt)
        roads = output['path']
        if roads == 'none':
            pretty_print(f'Error 402: no valid path found in plan: {plan}', 2)
            roads = None
    return roads



def generate_daily_activity_plan(persona, maze, population, perceived, traffic_state, retrieved):
    """
    Generate the daily activity plan that spans a day at the start of a day. 
    Traffic state not needed for making this plan.

    Args:
        persona (Persona): The Persona class instance
        maze (Maze): simulation world
        population (dict): dict that map persona name to Persona class instance; the population of the simulation world
        perceived (List[ConceptNode]): a list of retrieved memories
        traffic_state (str): traffic state description; NOT needed for making this plan. In fact it's empty.
        retrieved (List[ConceptNode]): a list of events; mainly those previewed events (e.g. there is an art exhibition today afternoon)
        
    Returns:
        a dict with keys 'datetime', 'reflection', 'plan', 'concepts'
        'datetime': the current tme
        'reflection': reflection on past days
        'plan': daily activity plan
        'concepts': a list of concepts that the persona want to keep to memory
    """
    # persona may want to chats with family member or friends to make the daily activity plan
    # no traffic state on the start of the day
    chat_summaries = chat(persona=persona, 
                          maze=maze, 
                          population=population, 
                          new_day=True, 
                          perceived=perceived, 
                          traffic_state=traffic_state, 
                          retrieved=retrieved)
    
    # check vehicle usage
    # Note: this is not needed for advanced LLMs with good instruction following ability
    # for weaker models, we recommend to add this for failsafe purpose
    num_family_vehicles = persona.st_mem.number_of_vehicles_in_family
    vehicle_used = False
    vehicle_used_name = None
    if num_family_vehicles == 0 or persona.st_mem.licensed_driver == False:
        chat_summaries += f"You cannot drive. Choose transit for travel today."
    elif num_family_vehicles == 1:
        for key, spouse_persona_name in persona.st_mem.other_family_members.items():
            if key == "husband" or key == "wife":
                spouse_persona = population[spouse_persona_name]
                if spouse_persona.st_mem.original_plans and spouse_persona.st_mem.original_plans[-1]['datetime'].day == persona.st_mem.curr_time.day:
                    current_plan = spouse_persona.st_mem.original_plans[-1]['plan']
                    for i in range(1, len(current_plan)):
                        if current_plan[i][3] == "drive":
                            vehicle_used = True
                            vehicle_used_name = spouse_persona_name
                            break
        if vehicle_used:
            chat_summaries += f"\n\nNote: the only vehicle of the family is already taken by {vehicle_used_name}; you must use transit for travel today!"
                            
    prompt_input = [config.simulation_description,  # 0 (str) simulation purpose description
                    maze.network_description,  # 1 (str) transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # 2 (str) persona description
                    persona.st_mem.curr_time.strftime("%a %Y-%m-%d"), # 3 (str) current date, e.g. Wed 2025-4-23
                    persona.st_mem.get_str_last_original_plan(new_day=True),  # 4 (str) last day's original plan as well as reflection in the morning
                    persona.st_mem.get_str_last_daily_reflection(),  # 5 (str) last day's daily reflection
                    convert_concept_nodes_to_str(persona.st_mem.curr_time, "perceived", perceived),  # 6 (str) perceived
                    convert_concept_nodes_to_str(persona.st_mem.curr_time, "retrieved", retrieved),  # 7 (str) retrieved
                    chat_summaries,  # 8 (str) summary of the chats
                    ]

    prompt_template = config.agent_path + "/llm_modules/prompt_templates/generate_daily_activity_plan_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    
    # failsafe
    # to avoid generating invalid facility names
    for attempt in range(config.max_num_retries):
        output= llm_generate_with_json_extraction_and_retries(prompt) #llm_generate(prompt)
        no_error = True
        for activity in output['plan']:
            if activity[0] not in maze.facilities_info:
                pretty_print(f"Error 004: invalid facility name {activity[0]} in the plan", 2)
                pretty_print(">>>Plan:<<<", 2)
                pretty_print(output['plan'], 2)
                pretty_print(f"Retrying for {attempt + 1} time...", 2)
                no_error = False
                break
        if no_error:
            break
    
    if not no_error:
        raise Exception("Error 007: failed to generate a valid plan")
    output['datetime'] = persona.st_mem.curr_time
    persona.st_mem.original_plans.append(output)
    
    
    # update cache file for frontend visualization (messages)
    json_path = 'gatsim/cache/curr_messages.json'
    content_to_write = "[reflect] " + output['reflection']
    update_cache_concurrent_safe(json_path, persona, content_to_write)
    
    # print out
    pretty_print()
    pretty_print(f">>> {persona.name} reflections:", 2)
    pretty_print()
    pretty_print(output['reflection'], 2)
    pretty_print()
    pretty_print(f">>> {persona.name} daily activity plan:", 2)
    pretty_print()
    pretty_print(output['plan'], 2)
    pretty_print()
    pretty_print(f">>> {persona.name} concepts:", 2)
    pretty_print()
    pretty_print(output['concepts'], 2)
    
    # add concepts to lt_mem
    for concept_tuple in output['concepts']:
        concept_nodes = convert_concept_tuple_to_concept_node(persona, maze, concept_tuple)
        for concept_node in concept_nodes:
            persona.lt_mem.add_concept_node(concept_node)
    
    # initialize the sleep activity to be the current activity
    # update current activity to be staying at home, and determine the duration depending on get-up time
    # '-1' for last plan; 'plan' to extract the plan; '0' for the first activity
    # Each activity is a list of six elements:
    #       0                      1                           2               3           4              5
    # [<activity_facility>, <activity_departure_time>, <reflect_every>, <travel_mode>, <path>, <activity_description>]
    # Note: the first activity of the day is sleeping
    # the first activity on the plan is the next activity in the future
    get_up_activity = persona.st_mem.original_plans[-1]['plan'][0]  # next activity is wake up routine
    
    # checks:
    # failsafe
    orig_plan =  persona.st_mem.original_plans[-1]['plan']
    # This first activity should set <reflect_every> to be 20. Only this very first activity can have <travel_mode> and <path> to be "none".
    get_up_activity[2] = 20
    get_up_activity[3] = "none"
    get_up_activity[4] = "none"
    # if go to school, set departure time to be "none"
    go_to_school_index = -1
    for i in range(len(orig_plan)):
        if orig_plan[i][0] == "School":
            go_to_school_index = i
            break
    if go_to_school_index > 0:
        orig_plan[i + 1][1] = "none"
    # last activity is going home before 22:00
    
    # set current activity
    persona.st_mem.activity_index = -1  # since current sleeping activity is not part of the plan
    persona.st_mem.activity_facility = persona.st_mem.home_facility  # sleep at home
    persona.st_mem.activity_departure_time = persona.st_mem.curr_time  # sleep activity start from 12:00 just for convenience; it does not means the actual going to bed time
    wake_up_time = convert_time_str_to_datetime(persona.st_mem.curr_time, get_up_activity[1])  # Note: departure time is string like "08:00"
    persona.st_mem.activity_duration = wake_up_time - persona.st_mem.activity_departure_time
    persona.st_mem.reflect_every = None  # No plan revision during sleep; namely sleep should not be interrupted
    persona.st_mem.travel_mode = None
    persona.st_mem.planned_path = None
    persona.st_mem.activity_description = "Sleeping at home."  # initialized to be "Sleeping at home."
    
    # update cache file for frontend visualization (plans)
    json_path = 'gatsim/cache/curr_plans.json'
    content_to_write = output['plan']
    update_cache_concurrent_safe(json_path, persona, content_to_write)
    
    

def chat(persona, maze, population, new_day, perceived, traffic_state, retrieved):
    """
    persona chatting with other people (family members or friends)
    
    Args:
        persona (Persona): the persona to initiate the chat
        maze (Maze): the simulation world
        population (dict): map persona name to Persona instance; the population in the simulation world
        new_day (bool): True if it's the start of a new day
        perceived (List[ConceptNode]): perceived events
        traffic_state (str): realtime traffic state
        retrieved (List[ConceptNode]): retrieved memories
        
    Returns:
        chat_summaries (str): chat summaries
    """
    if new_day:
        # if new day, context is:
        # last days' original plan 
        # + last day's daily reflection 
        # + perceived 
        # + retrieved
        chat_context = persona.st_mem.get_str_last_original_plan(new_day=True) + '\n' \
            + persona.st_mem.get_str_last_daily_reflection()  + '\n' \
            + convert_concept_nodes_to_str(persona.st_mem.curr_time, "perceived", perceived)  + '\n' \
            + convert_concept_nodes_to_str(persona.st_mem.curr_time, "retrieved", retrieved)
    else:
        # during the day, context is: 
        # today's original plan 
        # + today's revised plans 
        # + realtime traffic state 
        # + perceived 
        # + realtime traffic state 
        # + retrieved
        chat_context = persona.st_mem.get_str_last_original_plan(new_day=False)  + '\n' \
            + persona.st_mem.get_str_revised_plans()  + '\n' \
            + convert_concept_nodes_to_str(persona.st_mem.curr_time, "perceived", perceived)  + '\n' \
            + traffic_state  + '\n' \
            + convert_concept_nodes_to_str(persona.st_mem.curr_time, "retrieved", retrieved)
    
    # the return (will be assembled before return)
    chat_summaries_start = f"""
Summary of {persona.st_mem.name}'s current chats with other people (empty if no chat happened yet):
---CURRENT CHAT SUMMARY SECTION START---"""
    chat_summaries_body = ""  # append summary of new chats one by one later
    chat_summaries_end = """
---CURRENT CHAT SUMMARY SECTION END---"""

    # start chatting process
    for count in range(config.max_num_people_to_chat_with):  # a persona can only chat with max number of so many personas
        # update chat context
        chat_context_with_chat_summaries = chat_context + '\n' + chat_summaries_start + chat_summaries_body + chat_summaries_end
        other_persona_name, query = initiate_chat(persona, maze, new_day, chat_context_with_chat_summaries)
        if other_persona_name.lower() == "none":
            break
        
        pretty_print()
        pretty_print(f"{persona.st_mem.name} is chatting with {other_persona_name}", 2)
        # Note: chat summaries should be added
        
        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        content_to_write = f"[chat] {other_persona_name}, {query}"
        update_cache_concurrent_safe(json_path, persona, content_to_write)
        
        # get other persona chat context
        # failsafe; if population does not include other_persona_name info
        if other_persona_name not in population:
            chat_summaries_body += f'\n (unable to speak to {other_persona_name})'
            pretty_print()
            pretty_print(f"Error 008: {persona.st_mem.name} unable to speak to {other_persona_name}")
            continue
        
        # begin to chat with other persona
        other_persona = population[other_persona_name]
        other_persona_perceived, other_persona_traffic_state = perceive(other_persona, maze, population, save_memories=False)  
        # set save_memories to False for other persona when chatting to avoid duplicates
        other_persona_retrieved = other_persona.lt_mem.retrieve(perceived, maze)

        if new_day:
            other_persona_chat_context = other_persona.st_mem.get_str_last_original_plan(new_day=True) + '\n' \
            + other_persona.st_mem.get_str_last_daily_reflection() + '\n' \
            + convert_concept_nodes_to_str(other_persona.st_mem.curr_time, "perceived", other_persona_perceived)  + '\n' \
            + convert_concept_nodes_to_str(other_persona.st_mem.curr_time, "retrieved", other_persona_retrieved)
        else:
            other_persona_chat_context = other_persona.st_mem.get_str_last_original_plan(new_day=False) + '\n' \
            + persona.st_mem.get_str_revised_plans() + '\n' \
            + convert_concept_nodes_to_str(other_persona.st_mem.curr_time, "perceived", perceived)  + '\n' \
            + other_persona_traffic_state  + '\n' \
            + convert_concept_nodes_to_str(other_persona.st_mem.curr_time, "retrieved", retrieved)
                
        chat_history = f"Chat history between {persona.st_mem.name} and {other_persona_name}:"
        chat_history += f"\n{persona.st_mem.name}: {query}"
        
        for i in range(config.max_num_chat_rounds_per_conversation):
            # for respondent, we don't add perceived, retrieved, or chat_summaries
            response = generate_response(persona=other_persona, 
                                       maze=maze, 
                                       new_day=new_day,
                                       chat_context=other_persona_chat_context, 
                                       chat_history=chat_history)
            # update chat history
            if response.lower() == "none":
                break
            else:
                chat_history += f"\n{other_persona_name}: {response}"
            
            # update cache file for frontend visualization (messages)
            json_path = 'gatsim/cache/curr_messages.json'
            content_to_write = f"[chat] {persona.st_mem.name}, {response}"
            update_cache_concurrent_safe(json_path, other_persona, content_to_write)

            # persona response
            new_query = generate_response(persona=persona, 
                                       maze=maze,
                                       new_day=new_day,
                                       chat_context=chat_context_with_chat_summaries, 
                                       chat_history=chat_history)
            # Do you have more question?
            if new_query.lower() == "none":
                break
            else:
                # update cache file for frontend visualization (messages)
                json_path = 'gatsim/cache/curr_messages.json'
                content_to_write = f"[chat] {other_persona.st_mem.name}, {new_query}"
                update_cache_concurrent_safe(json_path, persona, content_to_write)
                
                chat_history += f"\n{persona.st_mem.name}: {new_query}"
                query = new_query
        pretty_print()
        pretty_print(f">>> Chat history of {persona.st_mem.name} and {other_persona_name}:", 2)
        pretty_print()
        pretty_print(chat_history, 2)
        pretty_print()
        chat_summary, keywords = generate_chat_summary(persona, other_persona, maze, chat_history)
        pretty_print(">>> Chat summary:", 2)
        pretty_print()
        pretty_print(chat_summary, 2)

        # add to memory of both persona and other_persona
        keywords = [k.strip() for k in keywords.split(',')]
        importance = generate_importance_score(persona, maze, 'chat', chat_summary)
        # Note: difference persona may view the same event differently
        chat_node = ConceptNode(type='chat',
                                created=persona.st_mem.curr_time,
                                content=chat_summary,
                                keywords=keywords,
                                spatial_scope=None,
                                time_scope=None,
                                importance=importance
                                )
        persona.lt_mem.add_concept_node(chat_node)
        importance = generate_importance_score(other_persona, maze, 'chat', chat_summary)
        chat_node = ConceptNode(type='chat',
                                created=other_persona.st_mem.curr_time,
                                content=chat_summary,
                                keywords=keywords,
                                spatial_scope=None,
                                time_scope=None,
                                importance=importance
                                )
        other_persona.lt_mem.add_concept_node(chat_node)
        # append to chat summaries
        chat_summaries_body += '\n' + chat_summary
        
    # construct the complete chat summary
    chat_summaries = chat_summaries_start + chat_summaries_body + chat_summaries_end  # update persona context with new chat summaries
    return chat_summaries
        

def initiate_chat(persona, maze, new_day, chat_context):
    """ 
    Persona initiate a chat if he or she wants to.
    
    Args:
        persona (Persona): persona to initiate the chat
        maze (Maze): the simulation world
        new_day (bool): True if it's start of a new day
        persona_context (str): context of the chat (par)
        
    Returns:
        respondent (str): name of the persona to respond
        query (str): the query to the respondent
    """
    if new_day:
        curr_time = persona.st_mem.curr_time.strftime("%a %Y-%m-%d")  # if it's the start of a new day, we just need to know the day
    else:
        curr_time = persona.st_mem.curr_time.strftime("%%a Y-%m-%d %H:%M")
    prompt_input = [config.simulation_description,  # 0 simulation purpose description
                    maze.network_description,  # 1 transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # 2 persona description
                    curr_time, # 3 current date or datetime
                    chat_context  # 4 chat context
                    ]  
    if new_day:
        prompt_template = config.agent_path + "/llm_modules/prompt_templates/initiate_chat_new_day_v1.txt"
    else:
        prompt_template = config.agent_path + "/llm_modules/prompt_templates/initiate_chat_during_day_v1.txt"
        
    prompt = generate_prompt(prompt_input, prompt_template)
    output= llm_generate_with_json_extraction_and_retries(prompt) #llm_generate(prompt)
    respondent = output['person_name']
    query = output['query']
    return respondent, query


def generate_response(persona, maze, new_day, chat_context, chat_history):
    """ 
    Persona generate a response give the chat_history and context.
    
    Args:
        persona (Persona): the persona to response
        maze (Maze): the simulation world
        new_day (bool): whether it's the start of a new day
        chat_context (str): chat context
        chat_history (str): previous chat rounds
        
    Returns:
        response (str): persona response
    """
    if new_day:
        curr_time = persona.st_mem.curr_time.strftime("%a %Y-%m-%d")
    else:
        curr_time = persona.st_mem.curr_time.strftime("%%a Y-%m-%d %H:%M")
    prompt_input = [config.simulation_description,  # 0 simulation purpose description
                maze.network_description,  # 1 transportation environment description
                persona.st_mem.get_str_persona_identity(),  # 2 persona description
                curr_time, # 3 current datetime
                chat_context, # 4 chat context
                chat_history,  # 5 chat history with the respondent (may be empty)
                ]
    prompt_template = config.agent_path + "/llm_modules/prompt_templates/generate_response_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output= llm_generate_with_json_extraction_and_retries(prompt) #llm_generate(prompt)
    response = output['response']
    return response


def generate_chat_summary(persona, other_persona, maze, chat_history):
    """ 
    Summary a chat.
    
    Args:
        chat_history (str): chat between two personas
    
    Returns (str): 
        content (str): chat summary
        keywords (str): keywords of chat
    """
    prompt_input = [config.simulation_description,  # 0 simulation purpose description
                maze.network_description,  # 1 transportation environment description
                persona.st_mem.get_str_persona_identity(),  # 2 persona description
                other_persona.st_mem.get_str_persona_identity(),  # 3 other persona description
                chat_history  # 4 chat history
                ]
    prompt_template = config.agent_path + "/llm_modules/prompt_templates/generate_chat_summary_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output= llm_generate_with_json_extraction_and_retries(prompt) #llm_generate(prompt)
    summary = output['summary']
    keywords = output['keywords']
    return summary, keywords


def update_daily_activity_plan(persona, maze, population, perceived, traffic_state, retrieved):
    """ 
    Update daily plan if needed.
    
    Args:
        persona (Persona): persona making the plan
        maze (Maze): the maze class object of the world
        population (dict): the population of the world
        perceived (list[ConceptNode]): perceived events of the persona
        traffic_state (str): description of the realtime traffic state
        retrieved (list[ConceptNode]):  retrieved events of the persona
    
    Returns:
        True if activity plan revised; False otherwise.
    """
    # chat if needed
    # Does persona needs to chat? if so, who? and generate chats. we should avoid infinite chatting between two agents.
    # the conversation may also influence the other persona's daily activity plan; but we don't update the other persona's activity here
    # we add conversation to the other persona long term memory;
    # and we make sure that recent conversation is retrieved
    chat_summaries = chat(persona=persona, 
                          maze=maze, 
                          population=population, 
                          new_day=False, 
                          perceived=perceived, 
                          traffic_state=traffic_state, 
                          retrieved=retrieved)
    
    # retrieve again
    # this time let agent to generate the query for retrieving form lt_mem
    # not implemented
    
    # check going back home activity
    # Note: this is not needed for advanced LLMs with good instruction following ability
    # for weaker models, we recommend to add this for failsafe purpose
    if persona.st_mem.curr_time.hour == 22 and persona.st_mem.curr_time.minute == 0:
        current_plan = persona.st_mem.revised_plans[-1]['plan'] if persona.st_mem.revised_plans else persona.st_mem.original_plans[-1]['plan']
        if persona.st_mem.curr_place != persona.st_mem.home_facility and \
            current_plan[-1][0] != persona.st_mem.home_facility:
            chat_summaries += f"\n\n Note: you need to back to home facility at {persona.st_mem.home_facility} now!"
    
    # prepare prompt input
    prompt_input = [config.simulation_description,  # 0 simulation purpose description
                    maze.network_description,  # 1 transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # 2 persona description
                    persona.st_mem.curr_time.strftime("%a %Y-%m-%d %H:%M"), # 3 current datetime
                    persona.st_mem.get_str_last_original_plan(new_day=False),  # 4 today original plan as well as reflection in the morning
                    persona.st_mem.get_str_revised_plans(),  # 5 today revised plans as well as reflections 
                    persona.st_mem.get_str_current_activity_and_status(),  # 6 current activity description
                    convert_concept_nodes_to_str(persona.st_mem.curr_time, "perceived", perceived),  # 7 current perceived events
                    traffic_state,  # 8 realtime traffic state
                    convert_concept_nodes_to_str(persona.st_mem.curr_time, "retrieved", retrieved),  # 9 current retrieved events or thoughts (may be empty)
                    chat_summaries,  # 10 chat summary
                    ]  

    prompt_template = config.agent_path + "/llm_modules/prompt_templates/update_daily_activity_plan_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    
    # failsafe
    # to avoid generating invalid facility names
    for attempt in range(config.max_num_retries):
        output= llm_generate_with_json_extraction_and_retries(prompt) #llm_generate(prompt)
        plan = output['plan']
        no_error = True
        if isinstance(plan, list):  # we only check when a plan list is returned
            for activity in plan:
                if activity[0] not in maze.facilities_info:
                    pretty_print(f"Error 009: invalid facility name {activity[0]} in the plan", 2)
                    pretty_print(f">>>Plan:<<<", 2)
                    pretty_print(output['plan'], 2)
                    pretty_print(f'Retrying for the {attempt+1} time...', 2)
                    no_error = False
                    break
            if no_error:
                break
        else:
            break
    
    if not no_error:
        raise Exception("Error 010: failed to generate a valid plan")
    # print out
    pretty_print()
    pretty_print(f">>> {persona.name} reflections:", 2)
    pretty_print()
    pretty_print(output['reflection'], 2)
    pretty_print()
    pretty_print(f">>> {persona.name} daily activity plan:", 2)
    pretty_print()
    pretty_print(output['plan'], 2)
    pretty_print()
    pretty_print(f">>> {persona.name} concepts:", 2)
    pretty_print()
    pretty_print(output['concepts'], 2)
    # add concepts to lt_mem
    for concept_tuple in output['concepts']:
        concept_nodes = convert_concept_tuple_to_concept_node(persona, maze, concept_tuple)
        for concept_node in concept_nodes:
            persona.lt_mem.add_concept_node(concept_node)
    
    plan = output['plan']
    # Each activity is a list of six elements:
    #           0                   1                       2               3           4              5
    # [<activity_facility>, <activity_departure_time>, <reflect_every>, <travel_mode>, <path>, <activity_description>]
    # update plan
    if isinstance(plan, str) and plan.lower() == 'none':
        # case 1) no revision
        update_info = f"{persona.name} - plan not revised"
        pretty_print(update_info, 2)
    elif isinstance(plan, str) and plan.lower() == 'update path: shortest':
        # case 2) no changes are made to the plan; but update path to realtime shortest (mobility update)
        persona.st_mem.planned_path = maze.get_shortest_path(persona.st_mem.curr_place, persona.st_mem.activity_facility, persona.st_mem.travel_mode)['original_path']
        update_info = f"{persona.name} update current path to real-time shortest"
        pretty_print()
        pretty_print(update_info, 2)
        pretty_print("persona.st_mem.planned_path:", 2)
        pretty_print(persona.st_mem.planned_path, 2)
        
        persona.st_mem.plan_revision_description += f"""
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections: 
{output['reflection']}
Plan revisions:
{update_info}
"""

        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        content_to_write = f"[reflect] {output['reflection']}\nI will change path to real-time shortest path."
        update_cache_concurrent_safe(json_path, persona, content_to_write)

    elif isinstance(plan, str) and "update" in plan.lower() and "path" in plan.lower():
        # case 3) no changes made to plan, but a new path is given (mobility update)
        roads = extract_path(plan)
        if roads is None:
            return
        persona.st_mem.planned_path = maze.convert_path_format(persona.st_mem.curr_place, persona.st_mem.activity_facility, persona.st_mem.travel_mode, roads)
        update_info = f"{persona.name} update current path to {roads}"
        persona.st_mem.plan_revision_description += f"""
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections:
{output['reflection']}
Plan revisions:
{update_info}
"""

        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        content_to_write = f"[reflect] {output['reflection']}\nI will change path to {roads}"
        update_cache_concurrent_safe(json_path, persona, content_to_write)

        pretty_print()
        pretty_print(update_info, 2)
        pretty_print(persona.st_mem.planned_path, 2)
        
    elif isinstance(plan, str) and "update departure time" in plan:
        # case 4) update departure time of next activity
        tmp = plan.split(':')  # plan example: 'update departure time: 11:30'
        next_activity_departure_time = tmp[1].strip() + ":" + tmp[2].strip()
        next_activity_index = persona.st_mem.activity_index + 1
        current_plan = persona.st_mem.revised_plans[-1]['plan'] if persona.st_mem.revised_plans else persona.st_mem.original_plans[-1]['plan']
        if next_activity_index >= len(current_plan):
            # failsafe
            # no change to plan
            pretty_print()
            pretty_print(f"Error 011: {persona.name} - next activity index {next_activity_index} is out of range", 2)
            return
        current_plan[next_activity_index][1] = next_activity_departure_time  # Note: use string; since in plan we use string like "11:30" for departure time
        next_activity_facility = current_plan[next_activity_index][0]
        update_info = f"{persona.name} update the departure time of next activity at {next_activity_facility} to {next_activity_departure_time}"
        persona.st_mem.plan_revision_description += f"""
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections: 
{output['reflection']}
Plan revisions:
{update_info}
"""
        pretty_print()
        pretty_print(update_info, 2)
        pretty_print(persona.st_mem.planned_path, 2)
        
        # also update the duration of current activity!
        # convert to datetime obj before doing difference
        next_activity_departure_time = convert_time_str_to_datetime(persona.st_mem.curr_time, next_activity_departure_time)
        persona.st_mem.activity_duration = next_activity_departure_time - persona.st_mem.activity_departure_time
        
        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        content_to_write = f"[reflect] {output['reflection']}\nI will change next activity departure time to {next_activity_departure_time}."
        update_cache_concurrent_safe(json_path, persona, content_to_write)
        
        # update cache file for frontend visualization (plans)
        json_path = 'gatsim/cache/curr_plans.json'
        content_to_write =  current_plan
        update_cache_concurrent_safe(json_path, persona, content_to_write)
        
    elif isinstance(plan, list):
        # case 5) update the whole plan
        output['datetime'] = persona.st_mem.curr_time
        persona.st_mem.revised_plans.append(output)  # a new plan is added to revised_plans
        
        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        content_to_write = f"[reflect] {output['reflection']}\nI will revise my plan."
        update_cache_concurrent_safe(json_path, persona, content_to_write)
                
        # update cache file for frontend visualization (plans)
        json_path = 'gatsim/cache/curr_plans.json'
        content_to_write = plan
        update_cache_concurrent_safe(json_path, persona, content_to_write)
        
        first_activity = plan[0]
        persona.st_mem.activity_index = -1 
        # remember to update activity index in the new plan
        # the on-going activity is NOT included in the new plan
        # so we set activity index to -1
        
        # update on-going activity duration
        if first_activity[1] != 'none':
            first_activity_departure_time = convert_time_str_to_datetime(persona.st_mem.curr_time, first_activity[1])
            persona.st_mem.activity_duration = first_activity_departure_time - persona.st_mem.activity_departure_time
        else:
            persona.st_mem.activity_duration = None  # if the first activity is 'none', then the duration is None; which means depart immediately upon arrival
       
        update_info =  f"{persona.name} update future activity plan:\n{plan}"
        persona.st_mem.plan_revision_description += f"""
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections: 
{output['reflection']}
Plan revisions:
{update_info}
"""

    else:
        pretty_print(f"Error 505: {persona.name} update future activity plan:\n{plan}")
        raise Exception('Return error')
    