"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: run_prompt.py
Description: Defines all run gpt prompt functions. These functions directly
interface with the llm_safe_generate function.
"""
import re
import json
import datetime
import random
import string
import ast
from gatsim import config
from gatsim import utils
from gatsim.agent.llm_modules.llm import (generate_prompt, 
                                        llm_generate,
                                        llm_safe_generate, 
                                        llm_formated_safe_generate,
                                        print_run_prompts)


def generate_importance_score(persona, maze, event_type, content):
    prompt_input = [config.simulation_description,  # simulation purpose description
                    maze.network_description,  # transportation environment description
                    persona.st_mem.get_str_persona_identity(),  # persona description
                    event_type,
                    content
                    ]
    
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/generate_importance_score_v1.txt"
    prompt = generate_prompt(prompt_input, prompt_template)
    output= llm_generate(prompt)
    output = json.loads(output)
    return output['score']
    
    


















def get_random_alphanumeric(i=6, j=6): 
    """
    Returns a random alpha numeric string that has the length of somewhere
    between i and j. 

    Args: 
        i: min_range for the length
        j: max_range for the length
        
    Returns: 
        an alpha numeric str with the length of somewhere between i and j.
        
    Example Use Case:
    •	Unique Identifiers: It could be used for generating unique IDs or tokens in the project, 
 where a random alphanumeric string is required for identifying different agents, sessions, or objects within the system.
    •	Temporary Passwords or Keys: This function could also be useful for generating temporary passwords or keys for authentication.
    """
    k = random.randint(i, j)
    x = ''.join(random.choices(string.ascii_letters + string.digits, k=k))
    return x





def run_prompt_decide_to_talk(persona, target_persona, retrieved,test_input=None, 
                                                                             verbose=False): 
    def create_prompt_input(init_persona, target_persona, retrieved, 
                                                    test_input=None): 
        last_chat = init_persona.lt_mem.get_last_chat(target_persona.name)
        last_chatted_time = ""
        last_chat_about = ""
        if last_chat: 
            last_chatted_time = last_chat.created.strftime("%B %d, %Y, %H:%M:%S")
            last_chat_about = last_chat.description

        context = ""
        for c_node in retrieved["events"]: 
            curr_desc = c_node.description.split(" ")
            curr_desc[2:3] = ["was"]
            curr_desc = " ".join(curr_desc)
            context +=  f"{curr_desc}. "
        context += "\n"
        for c_node in retrieved["thoughts"]: 
            context +=  f"{c_node.description}. "

        curr_time = init_persona.st_mem.curr_time.strftime("%B %d, %Y, %H:%M:%S %p")
        init_act_desc = init_persona.st_mem.activity_description
        if "(" in init_act_desc: 
            init_act_desc = init_act_desc.split("(")[-1][:-1]
        
        if len(init_persona.st_mem.planned_path) == 0 and "waiting" not in init_act_desc: 
            init_p_desc = f"{init_persona.name} is already {init_act_desc}"
        elif "waiting" in init_act_desc:
            init_p_desc = f"{init_persona.name} is {init_act_desc}"
        else: 
            init_p_desc = f"{init_persona.name} is on the way to {init_act_desc}"

        target_act_desc = target_persona.st_mem.activity_description
        if "(" in target_act_desc: 
            target_act_desc = target_act_desc.split("(")[-1][:-1]
        
        if len(target_persona.st_mem.planned_path) == 0 and "waiting" not in init_act_desc: 
            target_p_desc = f"{target_persona.name} is already {target_act_desc}"
        elif "waiting" in init_act_desc:
            target_p_desc = f"{init_persona.name} is {init_act_desc}"
        else: 
            target_p_desc = f"{target_persona.name} is on the way to {target_act_desc}"

        prompt_input = []
        prompt_input += [context]

        prompt_input += [curr_time]

        prompt_input += [init_persona.name]
        prompt_input += [target_persona.name]
        prompt_input += [last_chatted_time]
        prompt_input += [last_chat_about]


        prompt_input += [init_p_desc]
        prompt_input += [target_p_desc]
        prompt_input += [init_persona.name]
        prompt_input += [target_persona.name]
        return prompt_input
    
    def __func_validate(gpt_response, prompt=""): 
        try: 
            if gpt_response.split("Answer in yes or no:")[-1].strip().lower() in ["yes", "no"]: 
                return True
            return False     
        except:
            return False 

    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split("Answer in yes or no:")[-1].strip().lower()

    def get_fail_safe(): 
        fs = "yes"
        return fs

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 20, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/decide_to_talk_v2.txt"
    prompt_input = create_prompt_input(persona, target_persona, retrieved,
                                                                         test_input)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]









def run_prompt_decide_to_react(persona, target_persona, retrieved,test_input=None, 
                                                                             verbose=False): 
    def create_prompt_input(init_persona, target_persona, retrieved, 
                                                    test_input=None): 

        context = ""
        for c_node in retrieved["events"]: 
            curr_desc = c_node.description.split(" ")
            curr_desc[2:3] = ["was"]
            curr_desc = " ".join(curr_desc)
            context +=  f"{curr_desc}. "
        context += "\n"
        for c_node in retrieved["thoughts"]: 
            context +=  f"{c_node.description}. "

        curr_time = init_persona.st_mem.curr_time.strftime("%B %d, %Y, %H:%M:%S %p")
        init_act_desc = init_persona.st_mem.activity_description
        if "(" in init_act_desc: 
            init_act_desc = init_act_desc.split("(")[-1][:-1]
        if len(init_persona.st_mem.planned_path) == 0: 
            loc = ""
            if ":" in init_persona.st_mem.activity_facility:
                loc = init_persona.st_mem.activity_facility.split(":")[-1] + " in " + init_persona.st_mem.activity_facility.split(":")[-2]
            init_p_desc = f"{init_persona.name} is already {init_act_desc} at {loc}"
        else: 
            loc = ""
            if ":" in init_persona.st_mem.activity_facility:
                loc = init_persona.st_mem.activity_facility.split(":")[-1] + " in " + init_persona.st_mem.activity_facility.split(":")[-2]
            init_p_desc = f"{init_persona.name} is on the way to {init_act_desc} at {loc}"

        target_act_desc = target_persona.st_mem.activity_description
        if "(" in target_act_desc: 
            target_act_desc = target_act_desc.split("(")[-1][:-1]
        if len(target_persona.st_mem.planned_path) == 0: 
            loc = ""
            if ":" in target_persona.st_mem.activity_facility:
                loc = target_persona.st_mem.activity_facility.split(":")[-1] + " in " + target_persona.st_mem.activity_facility.split(":")[-2]
            target_p_desc = f"{target_persona.name} is already {target_act_desc} at {loc}"
        else: 
            loc = ""
            if ":" in target_persona.st_mem.activity_facility:
                loc = target_persona.st_mem.activity_facility.split(":")[-1] + " in " + target_persona.st_mem.activity_facility.split(":")[-2]
            target_p_desc = f"{target_persona.name} is on the way to {target_act_desc} at {loc}"

        prompt_input = []
        prompt_input += [context]
        prompt_input += [curr_time]
        prompt_input += [init_p_desc]
        prompt_input += [target_p_desc]

        prompt_input += [init_persona.name]
        prompt_input += [init_act_desc]
        prompt_input += [target_persona.name]
        prompt_input += [target_act_desc]

        prompt_input += [init_act_desc]
        return prompt_input
    
    def __func_validate(gpt_response, prompt=""): 
        try: 
            if gpt_response.split("Answer: Option")[-1].strip().lower() in ["3", "2", "1"]: 
                return True
            return False     
        except:
            return False 

    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split("Answer: Option")[-1].strip().lower() 

    def get_fail_safe(): 
        fs = "3"
        return fs

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 20, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/decide_to_react_v1.txt"
    prompt_input = create_prompt_input(persona, target_persona, retrieved,
                                                                         test_input)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]






def run_prompt_create_conversation(persona, target_persona, curr_loc,
                                                                             test_input=None, verbose=False): 
    def create_prompt_input(init_persona, target_persona, curr_loc, 
                                                    test_input=None): 

        prev_convo_insert = "\n"
        if init_persona.lt_mem.seq_chats: 
            for i in init_persona.lt_mem.seq_chats: 
                if i.object == target_persona.st_mem.name: 
                    v1 = int((init_persona.st_mem.curr_time - i.created).total_seconds()/60)
                    prev_convo_insert += f'{str(v1)} minutes ago, they had the following conversation.\n'
                    for row in i.filling: 
                        prev_convo_insert += f'{row[0]}: "{row[1]}"\n'
                    break
        if prev_convo_insert == "\n": 
            prev_convo_insert = ""
        if init_persona.lt_mem.seq_chats: 
            if int((init_persona.st_mem.curr_time - init_persona.lt_mem.seq_chats[-1].created).total_seconds()/60) > 480: 
                prev_convo_insert = ""


        init_persona_thought_nodes = init_persona.lt_mem.retrieve_relevant_thoughts(target_persona.st_mem.activity_event[0],
                                                                target_persona.st_mem.activity_event[1],
                                                                target_persona.st_mem.activity_event[2])
        init_persona_thought = ""
        for i in init_persona_thought_nodes: 
            init_persona_thought += f"-- {i.description}\n"

        target_persona_thought_nodes = target_persona.lt_mem.retrieve_relevant_thoughts(init_persona.st_mem.activity_event[0],
                                                                init_persona.st_mem.activity_event[1],
                                                                init_persona.st_mem.activity_event[2])
        target_persona_thought = ""
        for i in target_persona_thought_nodes: 
            target_persona_thought += f"-- {i.description}\n"

        init_persona_curr_desc = ""
        if init_persona.st_mem.planned_path: 
            init_persona_curr_desc = f"{init_persona.name} is on the way to {init_persona.st_mem.activity_description}"
        else: 
            init_persona_curr_desc = f"{init_persona.name} is {init_persona.st_mem.activity_description}"

        target_persona_curr_desc = ""
        if target_persona.st_mem.planned_path: 
            target_persona_curr_desc = f"{target_persona.name} is on the way to {target_persona.st_mem.activity_description}"
        else: 
            target_persona_curr_desc = f"{target_persona.name} is {target_persona.st_mem.activity_description}"
 

        curr_loc = curr_loc["arena"]

        prompt_input = []
        prompt_input += [init_persona.st_mem.get_str_persona_identity()]
        prompt_input += [target_persona.st_mem.get_str_persona_identity()]

        prompt_input += [init_persona.name]
        prompt_input += [target_persona.name]
        prompt_input += [init_persona_thought]

        prompt_input += [target_persona.name]
        prompt_input += [init_persona.name]
        prompt_input += [target_persona_thought]

        prompt_input += [init_persona.st_mem.curr_time.strftime("%B %d, %Y, %H:%M:%S")]

        prompt_input += [init_persona_curr_desc]
        prompt_input += [target_persona_curr_desc]

        prompt_input += [prev_convo_insert]

        prompt_input += [init_persona.name]
        prompt_input += [target_persona.name]

        prompt_input += [curr_loc]
        prompt_input += [init_persona.name]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = (prompt + gpt_response).split("What would they talk about now?")[-1].strip()
        content = re.findall('"([^"]*)"', gpt_response)

        speaker_order = []
        for i in gpt_response.split("\n"): 
            name = i.split(":")[0].strip() 
            if name: 
                speaker_order += [name]

        ret = []
        for count, speaker in enumerate(speaker_order): 
            ret += [[speaker, content[count]]]

        return ret

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(init_persona, target_persona): 
        convo = [[init_persona.name, "Hi!"], 
                         [target_persona.name, "Hi!"]]
        return convo


    gpt_param = {"engine": "text-davinci-003", "max_tokens": 1000, 
                             "temperature": 0.7, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/create_conversation_v2.txt"
    prompt_input = create_prompt_input(persona, target_persona, curr_loc, 
                                                                         test_input)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe(persona, target_persona)
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]










def run_prompt_summarize_conversation(persona, conversation, test_input=None, verbose=False): 
    def create_prompt_input(conversation, test_input=None): 
        convo_str = ""
        for row in conversation: 
            convo_str += f'{row[0]}: "{row[1]}"\n'

        prompt_input = [convo_str]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        ret = "conversing about " + gpt_response.strip()
        return ret

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "conversing with a housemate about morning greetings"

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 11") ########
    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/summarize_conversation_v1.txt" ########
    prompt_input = create_prompt_input(conversation, test_input)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = "conversing about what to eat for lunch" ########
    special_instruction = "The output must continue the sentence above by filling in the <fill in> tag. Don't start with 'this is a conversation about...' Just finish the sentence but do not miss any important details (including who are chatting)." ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]











def run_prompt_extract_keywords(persona, description, test_input=None, verbose=False): 
    def create_prompt_input(description, test_input=None): 
        if "\n" in description: 
            description = description.replace("\n", " <LINE_BREAK> ")
        prompt_input = [description]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        print ("???")
        print (gpt_response)
        gpt_response = gpt_response.strip().split("Emotive keywords:")
        factual = [i.strip() for i in gpt_response[0].split(",")]
        emotive = [i.strip() for i in gpt_response[1].split(",")]
        all_keywords = factual + emotive
        ret = []
        for i in all_keywords: 
            if i: 
                i = i.lower()
                if i[-1] == ".": 
                    i = i[:-1]
                ret += [i]
        print (ret)
        return set(ret)

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return []

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 50, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/get_keywords_v1.txt"
    prompt_input = create_prompt_input(description, test_input)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)


    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]











def run_prompt_keyword_to_thoughts(persona, keyword, concept_summary, test_input=None, verbose=False): 
    def create_prompt_input(persona, keyword, concept_summary, test_input=None): 
        prompt_input = [keyword, concept_summary, persona.name]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = gpt_response.strip()
        return gpt_response

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return ""

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 40, 
                             "temperature": 0.7, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/keyword_to_thoughts_v1.txt"
    prompt_input = create_prompt_input(persona, keyword, concept_summary)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]









def run_prompt_convo_to_thoughts(persona, 
                                init_persona_name,  
                                target_persona_name,
                                convo_str,
                                fin_target, test_input=None, verbose=False): 
    def create_prompt_input(init_persona_name,  
                            target_persona_name,
                            convo_str,
                            fin_target, test_input=None): 
        prompt_input = [init_persona_name,
                                        target_persona_name,
                                        convo_str,
                                        init_persona_name,
                                        fin_target]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = gpt_response.strip()
        return gpt_response

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return ""

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 40, 
                             "temperature": 0.7, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/convo_to_thoughts_v1.txt"
    prompt_input = create_prompt_input(init_persona_name,  
                                                                        target_persona_name,
                                                                        convo_str,
                                                                        fin_target)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]










def run_prompt_event_importance(persona, event_description, test_input=None, verbose=False): 
    def create_prompt_input(persona, event_description, test_input=None): 
        prompt_input = [persona.st_mem.name,
                                        persona.st_mem.get_str_persona_identity(),
                                        persona.st_mem.name,
                                        event_description]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = int(gpt_response.strip())
        return gpt_response

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return 4

    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/importance_event_v1.txt" ########
    prompt_input = create_prompt_input(persona, event_description)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = "5" ########
    special_instruction = "The output should ONLY contain ONE integer value on the scale of 1 to 10." ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                        __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]











def run_prompt_thought_importance(persona, event_description, test_input=None, verbose=False): 
    def create_prompt_input(persona, event_description, test_input=None): 
        prompt_input = [persona.st_mem.name,
                                        persona.st_mem.get_str_persona_identity(),
                                        persona.st_mem.name,
                                        event_description]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = int(gpt_response.strip())
        return gpt_response

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return 4

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 8") ########
    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/importance_thought_v1.txt" ########
    prompt_input = create_prompt_input(persona, event_description)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = "5" ########
    special_instruction = "The output should ONLY contain ONE integer value on the scale of 1 to 10." ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]










def run_prompt_chat_importance(persona, event_description, test_input=None, verbose=False): 
    def create_prompt_input(persona, event_description, test_input=None): 
        prompt_input = [persona.st_mem.name,
                                        persona.st_mem.get_str_persona_identity(),
                                        persona.st_mem.name,
                                        event_description]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = int(gpt_response.strip())
        return gpt_response

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return 4

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 9") ########
    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/importance_chat_v1.txt" ########
    prompt_input = create_prompt_input(persona, event_description)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = "5" ########
    special_instruction = "The output should ONLY contain ONE integer value on the scale of 1 to 10." ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]











def run_prompt_focal_pt(persona, statements, n, test_input=None, verbose=False): 
    def create_prompt_input(persona, statements, n, test_input=None): 
        prompt_input = [statements, str(n)]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = "1) " + gpt_response.strip()
        ret = []
        for i in gpt_response.split("\n"): 
            ret += [i.split(") ")[-1]]
        return ret

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(n): 
        return ["Who am I"] * n

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 12") ########
    gpt_param = {"engine": "text-davinci-003", "max_tokens": 150, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/generate_focal_pt_v1.txt"
    prompt_input = create_prompt_input(persona, statements, n)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe(n)
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]








    
def run_prompt_insight_and_guidance(persona, statements, n, test_input=None, verbose=False): 
    def create_prompt_input(persona, statements, n, test_input=None): 
        prompt_input = [statements, str(n)]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        gpt_response = "1. " + gpt_response.strip()
        ret = dict()
        for i in gpt_response.split("\n"): 
            row = i.split(". ")[-1]
            thought = row.split("(because of ")[0].strip()
            evi_raw = row.split("(because of ")[1].split(")")[0].strip()
            evi_raw = re.findall(r'\d+', evi_raw)
            evi_raw = [int(i.strip()) for i in evi_raw]
            ret[thought] = evi_raw
        return ret

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(n): 
        return ["I am hungry"] * n

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 150, 
                             "temperature": 0.5, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/insight_and_evidence_v1.txt"
    prompt_input = create_prompt_input(persona, statements, n)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe(n)
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]








def run_prompt_agent_chat_summarize_ideas(persona, target_persona, statements, curr_context, test_input=None, verbose=False): 
    def create_prompt_input(persona, target_persona, statements, curr_context, test_input=None): 
        prompt_input = [persona.st_mem.get_str_curr_date_aYmdHM(), curr_context, persona.st_mem.currently, 
                                        statements, persona.st_mem.name, target_persona.st_mem.name]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split('"')[0].strip()

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "..."

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 17") ########
    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/summarize_chat_ideas_v1.txt" ########
    prompt_input = create_prompt_input(persona, target_persona, statements, curr_context)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = 'Jane Doe is working on a project' ########
    special_instruction = 'The output should be a string that responds to the question.' ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]










def run_prompt_agent_chat_summarize_relationship(persona, target_persona, statements, test_input=None, verbose=False): 
    def create_prompt_input(persona, target_persona, statements, test_input=None): 
        prompt_input = [statements, persona.st_mem.name, target_persona.st_mem.name]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split('"')[0].strip()

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "..."

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 18") ########
    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/summarize_chat_relationship_v2.txt" ########
    prompt_input = create_prompt_input(persona, target_persona, statements)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = 'Jane Doe is working on a project' ########
    special_instruction = 'The output should be a string that responds to the question.' ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]









def run_prompt_agent_chat(maze, persona, target_persona,
                                                             curr_context, 
                                                             init_summ_idea, 
                                                             target_summ_idea, test_input=None, verbose=False): 
    def create_prompt_input(persona, target_persona, curr_context, init_summ_idea, target_summ_idea, test_input=None): 
        prev_convo_insert = "\n"
        if persona.lt_mem.seq_chats: 
            for i in persona.lt_mem.seq_chats: 
                if i.object == target_persona.st_mem.name: 
                    v1 = int((persona.st_mem.curr_time - i.created).total_seconds()/60)
                    prev_convo_insert += f'{str(v1)} minutes ago, {persona.st_mem.name} and {target_persona.st_mem.name} were already {i.description} This context takes place after that conversation.'
                    break
        if prev_convo_insert == "\n": 
            prev_convo_insert = ""
        if persona.lt_mem.seq_chats: 
            if int((persona.st_mem.curr_time - persona.lt_mem.seq_chats[-1].created).total_seconds()/60) > 480: 
                prev_convo_insert = ""
        print (prev_convo_insert)

        curr_sector = f"{maze.access_tile(persona.st_mem.curr_place)['sector']}"
        curr_arena= f"{maze.access_tile(persona.st_mem.curr_place)['arena']}"
        curr_place = f"{curr_arena} in {curr_sector}"
        

        prompt_input = [persona.st_mem.currently, 
                                        target_persona.st_mem.currently, 
                                        prev_convo_insert,
                                        curr_context, 
                                        curr_place,

                                        persona.st_mem.name,
                                        init_summ_idea, 
                                        persona.st_mem.name,
                                        target_persona.st_mem.name,

                                        target_persona.st_mem.name,
                                        target_summ_idea, 
                                        target_persona.st_mem.name,
                                        persona.st_mem.name,

                                        persona.st_mem.name]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        print (gpt_response)

        gpt_response = (prompt + gpt_response).split("Here is their conversation.")[-1].strip()
        content = re.findall('"([^"]*)"', gpt_response)

        speaker_order = []
        for i in gpt_response.split("\n"): 
            name = i.split(":")[0].strip() 
            if name: 
                speaker_order += [name]

        ret = []
        for count, speaker in enumerate(speaker_order): 
            ret += [[speaker, content[count]]]

        return ret

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "..."

    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/agent_chat_v1.txt" ########
    prompt_input = create_prompt_input(persona, target_persona, curr_context, init_summ_idea, target_summ_idea)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = '[["Jane Doe", "Hi!"], ["John Doe", "Hello there!"] ... ]' ########
    special_instruction = 'The output should be a list of list where the inner lists are in the form of ["<Name>", "<Utterance>"].' ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    # print ("HERE END JULY 23 -- ----- ") ########
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]









def run_prompt_summarize_ideas(persona, statements, question, test_input=None, verbose=False): 
    def create_prompt_input(persona, statements, question, test_input=None): 
        prompt_input = [statements, persona.st_mem.name, question]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split('"')[0].strip()

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "..."

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 16") ########
    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/summarize_ideas_v1.txt" ########
    prompt_input = create_prompt_input(persona, statements, question)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = 'Jane Doe is working on a project' ########
    special_instruction = 'The output should be a string that responds to the question.' ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]










def run_prompt_generate_next_convo_line(persona, interlocutor_desc, prev_convo, retrieved_summary, test_input=None, verbose=False): 
    def create_prompt_input(persona, interlocutor_desc, prev_convo, retrieved_summary, test_input=None): 
        prompt_input = [persona.st_mem.name, 
                                        persona.st_mem.get_str_persona_identity(),
                                        persona.st_mem.name, 
                                        interlocutor_desc, 
                                        prev_convo, 
                                        persona.st_mem.name,
                                        retrieved_summary, 
                                        persona.st_mem.name,]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split('"')[0].strip()

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "..."

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 250, 
                             "temperature": 1, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/generate_next_convo_line_v1.txt"
    prompt_input = create_prompt_input(persona, interlocutor_desc, prev_convo, retrieved_summary)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]









def run_prompt_generate_whisper_inner_thought(persona, whisper, test_input=None, verbose=False): 
    def create_prompt_input(persona, whisper, test_input=None): 
        prompt_input = [persona.st_mem.name, whisper]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split('"')[0].strip()

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "..."

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 50, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/whisper_inner_thought_v1.txt"
    prompt_input = create_prompt_input(persona, whisper)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]








def run_prompt_planning_thought_on_convo(persona, all_utt, test_input=None, verbose=False): 
    def create_prompt_input(persona, all_utt, test_input=None): 
        prompt_input = [all_utt, persona.st_mem.name, persona.st_mem.name, persona.st_mem.name]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""):
        return gpt_response.split('"')[0].strip()

    def __func_validate(gpt_response, prompt=""): 
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 

    def get_fail_safe(): 
        return "..."

    gpt_param = {"engine": "text-davinci-003", "max_tokens": 50, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/planning_thought_on_convo_v1.txt"
    prompt_input = create_prompt_input(persona, all_utt)
    prompt = generate_prompt(prompt_input, prompt_template)

    fail_safe = get_fail_safe()
    output = llm_safe_generate(prompt, gpt_param, 5, fail_safe,
                                                                     __func_validate, __func_clean_up)

    if config.debug or verbose: 
        print_run_prompts(prompt_template, persona, gpt_param, 
                                            prompt_input, prompt, output)
    
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]









def run_prompt_memo_on_convo(persona, all_utt, test_input=None, verbose=False): 
    def create_prompt_input(persona, all_utt, test_input=None): 
        prompt_input = [all_utt, persona.st_mem.name, persona.st_mem.name, persona.st_mem.name]
        return prompt_input
    
    def __func_clean_up(gpt_response, prompt=""): ############
        return gpt_response.strip()

    def __func_validate(gpt_response, prompt=""): ############
        try: 
            __func_clean_up(gpt_response, prompt)
            return True
        except:
            return False 
    def get_fail_safe(): 
        return "..."

    print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 15") ########
    gpt_param = {"engine": "text-davinci-002", "max_tokens": 15, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/memo_on_convo_v1.txt" ########
    prompt_input = create_prompt_input(persona, all_utt)  ########
    prompt = generate_prompt(prompt_input, prompt_template)
    example_output = 'Jane Doe was interesting to talk to.' ########
    special_instruction = 'The output should ONLY contain a string that summarizes anything interesting that the agent may have noticed' ########
    fail_safe = get_fail_safe() ########
    output = llm_formated_safe_generate(prompt, example_output, special_instruction, 3, fail_safe,
                                                                                    __func_validate, __func_clean_up, True)
    if output != False: 
        return output, [output, prompt, gpt_param, prompt_input, fail_safe]









def run_gpt_generate_safety_score(persona, comment, test_input=None, verbose=False): 
    def create_prompt_input(comment, test_input=None):
        prompt_input = [comment]
        return prompt_input

    def __chat_func_clean_up(gpt_response, prompt=""): 
        gpt_response = json.loads(gpt_response)
        return gpt_response["output"]

    def __chat_func_validate(gpt_response, prompt=""): 
        try: 
            fields = ["output"]
            response = json.loads(gpt_response)
            for field in fields: 
                if field not in response: 
                    return False
            return True
        except:
            return False 

    def get_fail_safe():
        return None

    print ("11")
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/anthromorphosization_v1.txt" 
    prompt_input = create_prompt_input(comment) 
    print ("22")
    prompt = generate_prompt(prompt_input, prompt_template)
    print (prompt)
    fail_safe = get_fail_safe() 
    output = llm_safe_generate(prompt, dict(), 3, fail_safe,
                                                __chat_func_validate, __chat_func_clean_up, verbose)
    print (output)
    
    gpt_param = {"engine": "text-davinci-003", "max_tokens": 50, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]










def extract_first_json_dict(data_str):
        # Find the first occurrence of a JSON object within the string
        start_idx = data_str.find('{')
        end_idx = data_str.find('}', start_idx) + 1

        # Check if both start and end indices were found
        if start_idx == -1 or end_idx == 0:
                return None

        # Extract the first JSON dictionary
        json_str = data_str[start_idx:end_idx]

        try:
                # Attempt to parse the JSON data
                json_dict = json.loads(json_str)
                return json_dict
        except json.JSONDecodeError:
                # If parsing fails, return None
                return None



def run_gpt_generate_iterative_chat_utt(maze, init_persona, target_persona, retrieved, curr_context, curr_chat, test_input=None, verbose=False): 
    def create_prompt_input(maze, init_persona, target_persona, retrieved, curr_context, curr_chat, test_input=None):
        persona = init_persona
        prev_convo_insert = "\n"
        if persona.lt_mem.seq_chats: 
            for i in persona.lt_mem.seq_chats: 
                if i.object == target_persona.st_mem.name: 
                    v1 = int((persona.st_mem.curr_time - i.created).total_seconds()/60)
                    prev_convo_insert += f'{str(v1)} minutes ago, {persona.st_mem.name} and {target_persona.st_mem.name} were already {i.description} This context takes place after that conversation.'
                    break
        if prev_convo_insert == "\n": 
            prev_convo_insert = ""
        if persona.lt_mem.seq_chats: 
            if int((persona.st_mem.curr_time - persona.lt_mem.seq_chats[-1].created).total_seconds()/60) > 480: 
                prev_convo_insert = ""
        print (prev_convo_insert)

        curr_sector = f"{maze.access_tile(persona.st_mem.curr_place)['sector']}"
        curr_arena= f"{maze.access_tile(persona.st_mem.curr_place)['arena']}"
        curr_place = f"{curr_arena} in {curr_sector}"

        retrieved_str = ""
        for key, vals in retrieved.items(): 
            for v in vals: 
                retrieved_str += f"- {v.description}\n"


        convo_str = ""
        for i in curr_chat:
            convo_str += ": ".join(i) + "\n"
        if convo_str == "": 
            convo_str = "[The conversation has not started yet -- start it!]"

        init_iss = f"Here is Here is a brief description of {init_persona.st_mem.name}.\n{init_persona.st_mem.get_str_persona_identity()}"
        prompt_input = [init_iss, init_persona.st_mem.name, retrieved_str, prev_convo_insert,
            curr_place, curr_context, init_persona.st_mem.name, target_persona.st_mem.name,
            convo_str, init_persona.st_mem.name, target_persona.st_mem.name,
            init_persona.st_mem.name, init_persona.st_mem.name,
            init_persona.st_mem.name
            ]
        return prompt_input

    def __func_clean_up(gpt_response, prompt=""): 
        gpt_response = extract_first_json_dict(gpt_response)

        cleaned_dict = dict()
        cleaned = []
        for key, val in gpt_response.items(): 
            cleaned += [val]
        cleaned_dict["utterance"] = cleaned[0]
        cleaned_dict["end"] = True
        if "f" in str(cleaned[1]) or "F" in str(cleaned[1]): 
            cleaned_dict["end"] = False

        return cleaned_dict

    def __func_validate(gpt_response, prompt=""): 
        print ("ugh...")
        try: 
            # print ("debug 1")
            # print (gpt_response)
            # print ("debug 2")

            print (extract_first_json_dict(gpt_response))
            # print ("debug 3")

            return True
        except:
            return False 

    def get_fail_safe():
        cleaned_dict = dict()
        cleaned_dict["utterance"] = "..."
        cleaned_dict["end"] = False
        return cleaned_dict

    print ("11")
    prompt_template = config.agent_path + "/chat_modules/prompt_templates/iterative_convo_v1.txt" 
    prompt_input = create_prompt_input(maze, init_persona, target_persona, retrieved, curr_context, curr_chat) 
    print ("22")
    prompt = generate_prompt(prompt_input, prompt_template)
    print (prompt)
    fail_safe = get_fail_safe() 
    output = llm_safe_generate(prompt, dict(), 3, fail_safe,
                                                __func_validate, __func_clean_up, verbose)
    print (output)
    
    gpt_param = {"engine": "text-davinci-003", "max_tokens": 50, 
                             "temperature": 0, "top_p": 1, "stream": False,
                             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]

