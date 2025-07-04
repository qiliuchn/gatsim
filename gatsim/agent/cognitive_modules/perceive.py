"""
File: perceive.py
Description: This defines the "Perceive" module for generative agents. 

This function gathers nearby events from the environment and then checks against the most recent events already stored in long term memory 
and update the perceived event to long term memory if it's new. 


# Transportation information used for decision making - four types of info:
 - nearby events, like car crash congestion (NetworkEvent); they are NetworkEvent then converted to ConceptNode;
 - broadcast news (like flooding, wildfire) (NetworkEVent); they are NetworkEvent then converted to ConceptNode;
 - network traffic state description (str); network level; only congestion information; acts like traffic congestion map;
 - transport experiences (ConceptNode); they are created after waiting on a link a or after a trip, then inserted to lt_mem;


# Events to be perceived:
 - 1) current effective nearby network events (list[NetworkEvent])
 - 2) current effective maze broadcast news (list[NetworkEvent obj])
 - 3) current family member state (expressed as events (list[ConceptNode]))
 - 4) current friends state (expressed as events (list[ConceptNode]))
 - 5) current within-same-facility personas state (expressed as events (list[ConceptNode]))
 - 6) network traffic state (str)
"""
from datetime import datetime, timedelta
from gatsim import config
from gatsim.utils import pretty_print
from gatsim.agent.memory_modules.long_term_memory import ConceptNode
from gatsim.agent.llm_modules.run_prompt import generate_importance_score


def convert_network_event_to_concept_node(persona, maze, network_event):
    """
    Convert network event object to concept node
    Real life events (like congestion, wildfire) need to be converted to "concepts" to be handled in a uniform way by later retrieval, reflection, etc. processes.
    
    Args:
        persona: the current persona
        
    Returns:
        a ConceptNode obj
    """
    type = "event"
    created = persona.st_mem.curr_time
    content = network_event.content
    keywords = network_event.keywords
    spatial_scope = network_event.spatial_scope
    time_scope = network_event.time_scope
    importance = generate_importance_score(persona, maze, type, content)
    concept_node = ConceptNode(type, created, content, keywords, spatial_scope, time_scope, importance)
    return concept_node


def perceive(persona, maze, population, save_memories=True): 
    """
    Perceives events around the persona and saves it to the lt_mem if it's new to the persona. 
    Persona first perceives the events nearby the persona, as determined by its 
    <vision_r>. If there are a lot of events happening within that radius, we 
    take the <spatial_att_bandwidth> of the closest events. 
    Finally, we check whether any of them are new, as determined by <retention>. If they are new, then we
    save them to lt_mem.
    
    if it's the start of a day, agent only perceive the broadcast events like "today there is a exhibition at the museum"

    Args:
        persona (Persona): An instance of <Persona> that represents the current persona. 
        maze (Maze): An instance of <Maze> that represents the current maze in which the persona is acting in. 
        population (dict): A dict that map persona_name to Persona objects; it includes all personas in the simulation.
        
    Returns: 
        ret_events (list[ConceptNode]): a list of <ConceptNode> that are perceived and new. 
        network_traffic_state_description (str)
    """  
    new_day = False
    last_time = persona.st_mem.curr_time - timedelta(minutes=config.minutes_per_step)
    if persona.st_mem.curr_time.day != last_time.day:
        new_day = True
    
    perceived_events = []  # list of concept nodes that are perceived and new
    
    #=========================== Step 1. Gather broadcast events ======================================
    broadcast_events_list = [event for event in maze.broadcast_news if event.preview_time <= persona.st_mem.curr_time <= (event.start_time + event.duration)]
    broadcast_events_list = [convert_network_event_to_concept_node(persona, maze, event) for event in  broadcast_events_list]
    perceived_events.extend(broadcast_events_list)
    
    
    #==================== Step 2. Gather Nearby Events ========================================
    if not new_day:
        # PERCEIVE EVENTS. 
        # We will perceive events that take place in the vision_r as the persona's current node
        # including facility, node, link events;
        # Stores (distance, event) pairs in percept_events_list.
        # sorted by distance
        # keep only spatial_att_bandwidth many events
        # Note: Network events can only be perceived after preview_time
        # and events after (start_time + duration) should be removed and undetectable
        nearby_events_list = maze.get_nearby_events(persona.st_mem.curr_place, config.spatial_att_bandwidth)
        # events that allow preview or is on going can be perceived.
        nearby_events_list = [event for event in nearby_events_list if event.preview_time <= persona.st_mem.curr_time <= (event.start_time + event.duration)]
        nearby_events_list = [convert_network_event_to_concept_node(persona, maze, event) for event in nearby_events_list]
        nearby_events_list = [event for event in nearby_events_list if event not in perceived_events]  # Remove duplicates
        perceived_events.extend(nearby_events_list)

    #======================== Step 3. Get family members' events ================================
    # get family members' activities
    # no bandwidth; all events are perceived
    if not new_day:
        family_events_list = []
        for key, tmp_persona_name in persona.st_mem.other_family_members.items():
            # failsafe
            if tmp_persona_name not in population:
                pretty_print()
                pretty_print(f"Error 005: {persona.name} cannot perceive {tmp_persona_name}", 2)
                continue
            activity_facility = population[tmp_persona_name].st_mem.activity_facility
            activity_description = population[tmp_persona_name].st_mem.activity_description
            curr_place = population[tmp_persona_name].st_mem.curr_place
            curr_status = population[tmp_persona_name].st_mem.curr_status
            content = f"{tmp_persona_name} current activity description: {activity_description}; current status: {curr_status}."
            keywords = [tmp_persona_name, activity_facility, curr_place]
            importance = generate_importance_score(persona, maze, "event", content)
            concept_node = ConceptNode("event", persona.st_mem.curr_time, content, keywords, None, None, importance)
            family_events_list.append(concept_node)
            
        perceived_events.extend(family_events_list)
        
    #========================= Step 4. Get friends' events =====================================
    # get friends events
    social_events_list = []
    if not new_day:
        for tmp_persona_name in persona.st_mem.friends:
            # failsafe
            if tmp_persona_name not in population:
                pretty_print()
                pretty_print(f'Error 006: {tmp_persona_name} cannot be accessed', 2)
                continue
            activity_facility = population[tmp_persona_name].st_mem.activity_facility
            activity_description = population[tmp_persona_name].st_mem.activity_description
            curr_place = population[tmp_persona_name].st_mem.curr_place
            curr_status = population[tmp_persona_name].st_mem.curr_status
            content = f"{tmp_persona_name} current activity description: {activity_description} current status is {curr_status}."
            keywords = [tmp_persona_name, activity_facility, curr_place]
            importance = generate_importance_score(persona, maze, "event", content)
            node = ConceptNode("event", persona.st_mem.curr_time, content, keywords, None, None, importance)
            social_events_list.append(node)
    
    #============ Step 5. Get within-same-facility personas events ==============================
    # get nearby personas' events
    # friends and within-same-facility personas events share the same social_att_bandwidth
    # so store with the same list social_events_list
    if False:
        if not new_day:
            if persona.st_mem.curr_place in maze.facilities_info:  # if the persona is in a facility, not on road
                facility = persona.st_mem.curr_place
                for tmp_persona_name, tmp_persona in population.items():
                    if tmp_persona_name != persona.name:
                        if tmp_persona.st_mem.curr_place == facility:  # other persona in the same facility with current persona
                            activity_facility = population[tmp_persona_name].st_mem.activity_facility
                            activity_description = population[tmp_persona_name].st_mem.activity_description
                            curr_place = population[tmp_persona_name].st_mem.curr_place
                            curr_status = population[tmp_persona_name].st_mem.curr_status
                            content = f"{tmp_persona_name} current activity description: {activity_description}; current status is {curr_status}."
                            keywords = [tmp_persona_name, activity_facility, curr_place]
                            importance = generate_importance_score(persona, maze, "event", content)
                            concept_node = ConceptNode("event", persona.st_mem.curr_time, content, keywords, None, None, importance)
                            social_events_list.append(concept_node)
    
    # sort by importance and keep only social_att_bandwidth many events
    if not new_day:
        perceived_events.extend(sorted(social_events_list, key=lambda x: x.importance)[-config.social_att_bandwidth:])

    # avoid duplicates
    # Remove duplicate events based on content comparison
    seen_contents = set()
    unique_perceived_events = []
    for event in perceived_events:
        if event.content not in seen_contents:
            seen_contents.add(event.content)
            unique_perceived_events.append(event)
    # Update perceived_events to contain only unique events
    perceived_events = unique_perceived_events
    
    #===== Step 6. Check for New Events & Update long term memory; return Newly Perceived Events=====
    # Note: this part is NOT for retrieving events from the persona's long term memory; it's about updating the memory if needed.
    # <ret_events> is a list of <ConceptNode> instances from the persona's associative memory. 
    # - Each event is a 4-tuple: (subject, verb, object, desc). If the event is missing a verb, it’s treated as ("X", "is", "idle", "idle").
    # - desc is a short textual description (e.g., "bed is unmade").
    # - latest_events: The agent fetches recent events from memory, based on config.retention (how far back it remembers).
    ret_events = perceived_events
    if save_memories:
    # Avoid duplicates to memory; maybe the same event is perceived multiple times in a short term.
        for event in perceived_events: 
            # We retrieve the latest config.retention events. If there is  
            # something new that is happening (that is, event_svo not in latest_events),
            # then we add that event to the lt_mem and return it.
            
            # If this event is truly new (event_svo not in latest_events), the code:
            # add this event to memory
            # here we just need to invoke add_concept_node method; it will handle this automatically
            persona.lt_mem.add_concept_node(event)
            #persona.st_mem.importance_trigger_curr -= event.importance
            #persona.st_mem.importance_ele_n += 1
        
    #================== Step 7. get traffic congestion condition ================================
    # realtime traffic congestion
    # must be new;
    # we just returned it as description string.
    if not new_day:
        network_traffic_state_description = maze.get_road_congestion_info()
    else:
        network_traffic_state_description = ""
    
    traffic_state =  f"""
Real-time network traffic state (empty if no traffic state available):
---TRAFFIC STATE SECTION START---
{network_traffic_state_description}
---TRAFFIC STATE SECTION END---"""
    return ret_events, traffic_state
