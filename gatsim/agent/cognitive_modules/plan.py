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
     2) retain the latest activity plan, but reroute to realtime shortest path (calling maze's find shortest path function); persona can change travel mode as well if it's feasible;
     3) retain the latest activity plan, but reroute to a give path (path provided); persona can change mode as well if it's feasible;
     4) revise the latest activity plan.
     
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
	•	This variable stores a list of (start node, end node, mode) representing the path the persona will follow to complete their current action.


## Plan variables:
- st_mem.original_plans: original plan made at the beginning of the day; one for each day;
- st_mem.revised_plans: revised plans made during current day.

A plan is a list of activities.
Each activity is a list of six elements:

[<activity_facility>, <activity_departure_time>, <reflect_every>, <travel_mode>, <path>, <activity_description>]

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
"""

import json
from datetime import datetime, time, timedelta
from gatsim import config
from gatsim.utils import extract_json_from_string, convert_time_str_to_datetime, pretty_print
from gatsim.agent.llm_modules.llm import llm_generate, generate_prompt
from gatsim.agent.llm_modules.run_prompt import generate_importance_score
from gatsim.agent.memory_modules.long_term_memory import (convert_concept_nodes_to_str, 
                                                          convert_concept_tuple_to_concept_node,
                                                          ConceptNode)


def generate_daily_activity_plan(persona, maze, population, perceived, retrieved):
    """
    Generate the daily activity plan that spans a day at the start of a day. 

    Args: 
        persona (Persona): The Persona class instance
        maze (Maze): simulation world
        population (dict): dict that map persona name to Persona class instance; the population of the simulation world
        retrieved (List[ConceptNode]): a list of events; mainly those previewed events (e.g. there is an art exhibition today afternoon)
        perceived (List[ConceptNode]): a list of retrieved memories
        
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
                          traffic_state=None, 
                          retrieved=retrieved)
    
    prompt_input = [config.simulation_description,  # 0 (str) simulation purpose description
                    maze.network_description,  # 1 (str) transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # 2 (str) persona description
                    persona.st_mem.curr_time.strftime("%a %Y-%m-%d"), # 3 (str) current date, e.g. Wed 2025-4-23
                    persona.st_mem.get_str_last_original_plan(new_day=True),  # 4 (str) last day's original plan as well as reflection in the morning
                    persona.st_mem.get_str_last_daily_reflection(),  # 5 (str) last day's daily reflection
                    convert_concept_nodes_to_str("perceived", perceived),  # 6 (str) perceived
                    convert_concept_nodes_to_str("retrieved", retrieved),  # 7 (str) retrieved
                    chat_summaries,  # 8 (str) summary of the chats
                    ]

    prompt_template = config.agent_path + "/chat_modules/prompt_templates/generate_daily_activity_plan_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output= llm_generate(prompt)
    output = extract_json_from_string(output)
    output['datetime'] = persona.st_mem.curr_time
    persona.st_mem.original_plans.append(output)
    
    # update cache file for frontend visualization (messages)
    json_path = 'gatsim/cache/curr_messages.json'
    with open(json_path, 'r') as f:
        data = json.load(f)
    data[persona.st_mem.name] =  "[reflect] " + output['reflection']
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    # update cache file for frontend visualization (plans)
    json_path = 'gatsim/cache/curr_plans.json'
    with open(json_path, 'r') as f:
        data = json.load(f)
    data[persona.st_mem.name] =  output['plan']
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    # print out
    print()
    pretty_print(f">>> {persona.name} reflections:", 2)
    print()
    pretty_print(output['reflection'], 2)
    print()
    pretty_print(f">>> {persona.name} daily activity plan:", 2)
    print()
    pretty_print(output['plan'], 2)
    print()
    pretty_print(f">>> {persona.name} concepts:", 2)
    print()
    pretty_print(output['concepts'], 2)
    
    # add concepts to lt_mem
    for concept_tuple in output['concepts']:
        concept_nodes = convert_concept_tuple_to_concept_node(persona, maze, concept_tuple)
        for concept_node in concept_nodes:
            persona.lt_mem.add_concept_node(concept_node)
    
    # update the sleep activity
    # update current activity to be staying at home, and determine the duration depending on get-up time
    # '-1' for last plan; 'plan' to extract the plan; '0' for the first activity
    # Each activity is a list of six elements:
    #       0                      1                           2               3           4              5
    # [<activity_facility>, <activity_departure_time>, <reflect_every>, <travel_mode>, <path>, <activity_description>]
    # Note: the first activity of the day is sleeping
    # the first activity on the plan is the next activity in the future
    get_up_activity = persona.st_mem.original_plans[-1]['plan'][0]  # next activity is wake up routine
    persona.st_mem.activity_index = -1  # this is special case for the start of the day
    persona.st_mem.activity_facility = persona.st_mem.home_facility  # sleep at home
    persona.st_mem.activity_departure_time = persona.st_mem.curr_time  # sleep activity start from 12:00 just for convenience; it does not means the actual sleeping time
    wake_up_time = convert_time_str_to_datetime(persona.st_mem.curr_time, get_up_activity[1])  # Note: departure time is string like "08:00"
    persona.st_mem.activity_duration = wake_up_time - persona.st_mem.activity_departure_time
    persona.st_mem.reflect_every = None  # No plan revision during sleep
    persona.st_mem.travel_mode = None
    persona.st_mem.planned_path = None
    persona.st_mem.activity_description = "Sleeping at home."
    

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
        # if new day, context is last days' original plan + last day's daily reflection + perceived + retrieved
        chat_context = persona.st_mem.get_str_last_original_plan(new_day=new_day)\
            + persona.st_mem.get_str_last_daily_reflection() \
            + convert_concept_nodes_to_str("perceived", perceived) \
            + convert_concept_nodes_to_str("retrieved", retrieved)
    else:
        # during the day, context is today's original + today's revised plans + realtime traffic state + perceived + realtime traffic state + retrieved
        chat_context = persona.st_mem.get_str_last_original_plan(new_day=False) \
            + persona.st_mem.get_str_revised_plans() \
            + convert_concept_nodes_to_str("perceived", perceived) \
            + traffic_state \
            + convert_concept_nodes_to_str("retrieved", retrieved)
    
    # the return
    chat_summaries_start = f"""
Summary of {persona.st_mem.name}'s chats with other people (empty if no chat has happened):
-----CHAT SUMMARY SECTION START-----"""
    chat_summaries_body = ""  # append summary of new chats one by one later
    chat_summaries_end = f"""
-----CHAT SUMMARY SECTION END-----"""

    # start chatting process
    for count in range(config.max_num_people_to_chat_with):  # a persona can only chat with max number of so many personas
        # update chat context
        chat_context_with_chat_summaries = chat_context + chat_summaries_start + chat_summaries_body + chat_summaries_end
        other_persona_name, query = initiate_chat(persona, maze, new_day, chat_context_with_chat_summaries)
        if other_persona_name.lower() == "none":
            break
        
        print()
        pretty_print(f"{persona.st_mem.name} is chatting with {other_persona_name}", 2)
        # Note: chat summaries should be added
        
        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data[persona.st_mem.name] = f"[chat] {other_persona_name}, {query}"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        
        # construct chat summary
        chat_summaries = chat_summaries_start + chat_summaries_body + chat_summaries_end  # update persona context with new chat summaries
        # get other persona chat context
        # no perceived, no retrieved
        other_persona = population[other_persona_name]
        if new_day:
            other_persona_chat_context = other_persona.st_mem.get_str_last_original_plan(new_day=True)
        else:
            other_persona_chat_context = other_persona.st_mem.get_str_last_original_plan(new_day=False) + persona.st_mem.get_str_revised_plans()
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
            with open(json_path, 'r') as f:
                data = json.load(f)
            data[other_persona.st_mem.name] = f"[chat] {persona.st_mem.name}, {response}"
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=4)
            
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
                with open(json_path, 'r') as f:
                    data = json.load(f)
                data[persona.st_mem.name] = f"[chat] {other_persona.st_mem.name}, {new_query}"
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                chat_history += f"\n{persona.st_mem.name}: {new_query}"
                query = new_query
        print()
        pretty_print(f">>> Chat history of {persona.st_mem.name} and {other_persona_name}:", 2)
        print()
        pretty_print(chat_history, 2)
        print()
        chat_summary, keywords = generate_chat_summary(persona, other_persona, maze, chat_history)
        pretty_print(">>> Chat summary:", 2)
        print()
        pretty_print(chat_summary, 2)

        # add to memory
        keywords = [k.strip() for k in keywords.split(',')]
        importance = generate_importance_score(persona, maze, 'chat', chat_summary)
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
        curr_time = persona.st_mem.curr_time.strftime("%a %Y-%m-%d")
    else:
        curr_time = persona.st_mem.curr_time.strftime("%%a Y-%m-%d %H:%M")
    prompt_input = [config.simulation_description,  # 0 simulation purpose description
                    maze.network_description,  # 1 transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # 2 persona description
                    curr_time, # 3 current date
                    chat_context  # 4 chat context
                    ]  
    if new_day:
        prompt_template = config.agent_path + "/chat_modules/prompt_templates/initiate_chat_new_day_v1.txt"
    else:
        prompt_template = config.agent_path + "/chat_modules/prompt_templates/initiate_chat_during_day_v1.txt"
        
    prompt = generate_prompt(prompt_input, prompt_template)
    output = llm_generate(prompt)
    output = extract_json_from_string(output)
    respondent = output['person name']
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
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/generate_response_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output = llm_generate(prompt)
    output = extract_json_from_string(output)
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
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/generate_chat_summary_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output = llm_generate(prompt)
    output = extract_json_from_string(output)
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
    
    # prepare prompt input
    prompt_input = [config.simulation_description,  # 0 simulation purpose description
                    maze.network_description,  # 1 transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # 2 persona description
                    persona.st_mem.curr_time.strftime("%a %Y-%m-%d %H:%M"), # 3 current date
                    persona.st_mem.get_str_last_original_plan(new_day=False),  # 4 today original plan as well as reflection in the morning
                    persona.st_mem.get_str_revised_plans(),  # 5 today revised plans as well as reflections 
                    persona.st_mem.get_str_current_activity_and_status(),  # 6 current activity description
                    convert_concept_nodes_to_str("perceived", perceived),  # 7 current perceived events
                    traffic_state,  # 8 realtime traffic state
                    convert_concept_nodes_to_str("retrieved", retrieved),  # 9 current retrieved events or thoughts (may be empty)
                    chat_summaries,  # 10 chat summary
                    ]  

    prompt_template = config.agent_path + "/chat_modules/prompt_templates/update_daily_activity_plan_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output= llm_generate(prompt)
    output = extract_json_from_string(output)
    # print out
    print()
    pretty_print(f">>> {persona.name} reflections:", 2)
    print()
    pretty_print(output['reflection'], 2)
    print()
    pretty_print(f">>> {persona.name} daily activity plan:", 2)
    print()
    pretty_print(output['plan'], 2)
    print()
    pretty_print(f">>> {persona.name} concepts:", 2)
    print()
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
        update_info = f"{persona.name} - path updated to realtime shortest"
        print()
        pretty_print(update_info, 2)
        pretty_print(persona.st_mem.planned_path, 2)
        
        persona.st_mem.plan_revision_description += f"""\n
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections: 
{output['reflection']}
Plan revisions: {update_info} """

        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data[persona.st_mem.name] = f"[reflect] {output['reflection']}\nI will change path to realtime shortest path."
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)


    elif isinstance(plan, str) and "update path" in plan.lower():
        # case 3) no changes made to plan, but a new path is given (mobility update)
        roads = plan.split(':')[1].strip()
        roads = [k.strip() for k in roads.split(',')]
        persona.st_mem.planned_path = maze.convert_path_format(persona.st_mem.curr_place, persona.st_mem.activity_facility, persona.st_mem.travel_mode, roads)
        update_info = f"{persona.name} - path updated to {roads}"
        persona.st_mem.plan_revision_description += f"""\n
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections: 
{output['reflection']}
Plan revisions: {update_info} """

        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data[persona.st_mem.name] = f"[reflect] {output['reflection']}\nI will change path to {roads}"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)

        print()
        pretty_print(update_info, 2)
        pretty_print(persona.st_mem.planned_path, 2)
        
    elif isinstance(plan, str) and "update departure time" in plan:
        # case 4) update departure time of next activity
        tmp = plan.split(':')  # plan example: 'update departure time: 11:30'
        next_activity_departure_time = tmp[1].strip() + ":" + tmp[2].strip()
        next_activity_index = persona.st_mem.activity_index + 1
        current_plan = persona.st_mem.revised_plans[-1]['plan'] if persona.st_mem.revised_plans else persona.st_mem.original_plans[-1]['plan']
        if next_activity_index >= len(current_plan):
            # fail safe
            # no change to plan
            print()
            pretty_print(f"{persona.name} - next activity index {next_activity_index} is out of range", 2)
            return
        current_plan[next_activity_index][1] = next_activity_departure_time  # Note: use string; since in plan we use string like "11:30" for departure time
        next_activity_facility = current_plan[next_activity_index][0]
        update_info = f"{persona.name} - next activity to {next_activity_facility} departure time updated to {next_activity_departure_time}"
        persona.st_mem.plan_revision_description += f"""\n
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections: 
{output['reflection']}
Plan revisions: {update_info} """
        print()
        pretty_print(update_info, 2)
        pretty_print(persona.st_mem.planned_path, 2)
        
        # also update the duration of current activity
        # convert to datetime obj before doing difference
        next_activity_departure_time = convert_time_str_to_datetime(persona.st_mem.curr_time, next_activity_departure_time)
        persona.st_mem.activity_duration = next_activity_departure_time - persona.st_mem.activity_departure_time
        
        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data[persona.st_mem.name] = f"[reflect] {output['reflection']}\nI will change next activity departure time to {next_activity_departure_time}."
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        # update cache file for frontend visualization (plans)
        json_path = 'gatsim/cache/curr_plans.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data[persona.st_mem.name] = current_plan
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        
    elif isinstance(plan, list):
        # case 5) update the whole plan
        output['datetime'] = persona.st_mem.curr_time
        persona.st_mem.revised_plans.append(output)  # a new plan is added to revised_plans
        
        # update cache file for frontend visualization (messages)
        json_path = 'gatsim/cache/curr_messages.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data[persona.st_mem.name] = f"[reflect] {output['reflection']}\nI will revise my plan."
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
            
        # update cache file for frontend visualization (plans)
        json_path = 'gatsim/cache/curr_plans.json'
        with open(json_path, 'r') as f:
            data = json.load(f)
        data[persona.st_mem.name] = plan
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        # update current activity
        first_activity = plan[0]
        persona.st_mem.activity_index = 0  # remember to update activity index in the new plan
        # departure time
        if persona.st_mem.activity_facility == first_activity[0]:
            # the current activity is kept, update path and travel mode of current activity if needed
            # departure time no need to change; LLM is instructed to keep the original departure time
            persona.st_mem.activity_departure_time = convert_time_str_to_datetime(persona.st_mem.curr_time, first_activity[1])
        else:
            # the current activity is NOT kept
            persona.st_mem.activity_facility = first_activity[0]
            persona.st_mem.activity_departure_time = persona.st_mem.curr_time
        # activity duration
        if len(plan) > 1:
            # if first activity is not last activity
            second_activity = plan[1]
            second_activity_departure_time = convert_time_str_to_datetime(persona.st_mem.curr_time, second_activity[1])
            persona.st_mem.activity_duration = second_activity_departure_time - persona.st_mem.activity_departure_time
        else:
            # if first activity is the last going back home activity, set duration to None
            persona.st_mem.activity_duration = timedelta(hours=24)
        # reflect every
        reflect_every_str =first_activity[2]
        if reflect_every_str == 'none':
            persona.st_mem.reflect_every = None
        else:
            persona.st_mem.reflect_every = timedelta(minutes=int(reflect_every_str))
            # enforce the constraints on reflect_every
            if persona.st_mem.activity_facility == persona.st_mem.work_facility:
                persona.st_mem.reflect_every = max(persona.st_mem.reflect_every, timedelta(minutes=config.min_work_reflect_every))
            else:
                persona.st_mem.reflect_every = max(persona.st_mem.reflect_every, timedelta(minutes=config.min_reflect_every))
        # travel mode
        persona.st_mem.travel_mode = first_activity[3]
        # path
        if first_activity[4] == "none":
            # no need to find path
            persona.st_mem.planned_path = []
        elif first_activity[4] == "shortest":
            # if use realtime shortest path
            if persona.st_mem.curr_place == first_activity[0]:
                # no need to find path if the current place is the same as the first activity
                persona.st_mem.planned_path = []
            else:
                persona.st_mem.planned_path = maze.get_shortest_path(persona.st_mem.curr_place, first_activity[0], travel_mode=persona.st_mem.travel_mode)['original_path']
        else:
            # if persona specified a path
            roads = [k.strip() for k in first_activity[4].split(',')]
            if persona.st_mem.curr_place == first_activity[0]:
                # no need to find path if the current place is the same as the first activity
                persona.st_mem.planned_path = []
            else:
                persona.st_mem.planned_path = maze.convert_path_format(persona.st_mem.curr_place, first_activity[0], persona.st_mem.travel_mode, roads)
        # activity description
        persona.st_mem.activity_description = first_activity[5]
       
        update_info =  f"{persona.name} - plan updated to:\n{plan}"
        persona.st_mem.plan_revision_description += f"""\n
Time: {persona.st_mem.curr_time.strftime('%H:%M')}
Reflections: 
{output['reflection']}
Plan revisions: {update_info} """
    else:
        raise Exception('Return error')
    