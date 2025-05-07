from datetime import datetime, time, timedelta
from gatsim import config
from gatsim.utils import extract_json_from_string, pretty_print
from gatsim.agent.llm_modules.llm import llm_generate, generate_prompt
from gatsim.agent.llm_modules.run_prompt import generate_importance_score
from gatsim.agent.memory_modules.long_term_memory import convert_concept_tuple_to_concept_node

def daily_reflection(persona, maze):
    """
    reflect using today's original plan (from lt_mem), and today's revised plans (from st_mem)
    and got the daily reflection (stored in lt_mem)
    """
    prompt_input = [config.simulation_description,  # 0) simulation purpose description
                    maze.network_description,  # 1) transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # 2) persona description
                    persona.st_mem.curr_time.strftime("%a %Y-%m-%d %H:%M"), # 3) current date
                    persona.st_mem.get_str_last_original_plan(new_day=False),  # 4) today original plan as well as reflection in the morning
                    persona.st_mem.get_str_revised_plans(),  # 5) today revised plans as well as reflections 
                    ] 
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/daily_reflection_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output = llm_generate(prompt)
    output = extract_json_from_string(output)
    # print out
    print()
    pretty_print(f"{persona.name} reflections:", 2)
    print()
    pretty_print(output['reflection'], 2)
    print()
    pretty_print(f"{persona.name} concepts:", 2)
    print()
    pretty_print(output['concepts'], 2)
    output['datetime'] = persona.st_mem.curr_time
    # add concepts to lt_mem
    for concept_tuple in output['concepts']:
        concept_nodes = convert_concept_tuple_to_concept_node(persona, maze, concept_tuple)
        for concept_node in concept_nodes:
            persona.lt_mem.add_concept_node(concept_node)
    # append to st_mem
    persona.st_mem.daily_reflections.append(output)
    
    

def reflection_trigger(persona): 
  """
  Given the current persona, determine whether the persona should run a 
  reflection. 
  
  Our current implementation checks for whether the sum of the new importance
  measure has reached the set (hyper-parameter) threshold.

  Args: 
    persona: Current Persona object
    
  Returns: 
    True if we are running a new reflection. False otherwise. 
  """
  pass






