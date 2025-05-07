"""
File: llm.py
Description: Wrapper functions for calling LLM APIs.
"""
import json
import time 
from gatsim import config
from gatsim.utils import extract_json_from_string


def temp_sleep(seconds=0.1):
    time.sleep(seconds)


def generate_prompt(curr_input, prompt_lib_file): 
    """
    Takes in the current input (e.g. comment that you want to classify) and 
    the path to a prompt file. The prompt file contains the raw str prompt that
    will be used, which contains the following substr: !<Args:>! -- this 
    function replaces this substr with the actual curr_input to produce the 
    final promopt that will be sent to the GPT3 server. 
    ARGS:
        curr_input: the input we want to feed in (IF THERE ARE MORE THAN ONE
                                Args:, THIS CAN BE A LIST.)
        prompt_lib_file: the path to the promopt file. 
    RETURNS: 
        a str prompt that will be sent to OpenAI's GPT server.  
    """
    if type(curr_input) == type("string"): 
        curr_input = [curr_input]
    curr_input = [str(i) for i in curr_input]

    #prompt_lib_file = 'gatsim/backend_server/' + prompt_lib_file
    f = open(prompt_lib_file, "r")
    prompt = f.read()
    f.close()
    for count, i in enumerate(curr_input):   
        prompt = prompt.replace(f"!<Args: {count}>!", i)
    if "<commentblockmarker>###</commentblockmarker>" in prompt: 
        prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
    return prompt.strip()


def llm_generate(prompt, gpt_parameter={}): 
    """ 
    Given a prompt and a dictionary of LLM parameters, make a request to LLM
    server and returns the response. 
    ARGS:
        prompt: a str prompt
        gpt_parameter: a python dictionary with the keys indicating the names of  
                                     the parameter and the values indicating the parameter 
                                     values.   
    RETURNS: 
        a str response. 
    """
    temp_sleep()
    completion = config.client.chat.completions.create(
        model=config.model_name, 
        messages=[{"role": "user", "content": prompt}]
    )
    completion = json.loads(completion.model_dump_json())
    return completion["choices"][0]["message"]["content"]



from sentence_transformers import SentenceTransformer
# model for embedding: sentence-transformer model
embedding_model_name="all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(embedding_model_name)

def get_embedding(text):
    """Get embedding for a given text."""
    
    if False:  # if True, use OpenAI API (Qwen model) for embedding
        text = text.replace("\n", " ")
        if not text: 
            text = "this is blank"
        completion = config.client.embeddings.create(
            model=config.model_name_text_embedding,
            input=text,
            dimensions=1024, # 指定向量维度（仅 text-embedding-v3 支持该参数）
            encoding_format="float"
        ) 
        completion = json.loads(completion.model_dump_json())
        return completion['data'][0]['embedding']
    
    embedding = embedding_model.encode([text])[0]
    return embedding

    

def llm_safe_generate(prompt, 
                    gpt_parameter,
                    repeat=5,
                    fail_safe_response="error",
                    func_validate=None,
                    func_clean_up=None,
                    verbose=False):
    """ 
    LLM safe generate response.
    Instruction is in prompt.
    No explicit json loading. 
    func_validate and func_clear_up are used for validation and cleaning up.
    """
    if verbose: 
        print ("PROMPT")
        print (prompt)

    for i in range(repeat): 
        curr_gpt_response = llm_generate(prompt, gpt_parameter)
        if verbose: 
            print ("---- repeat count: ", i)
            print (curr_gpt_response)
            print ("~~~~")
        if func_validate and func_clean_up:  # if func_validate and func_clean_up are provided, use them
            if func_validate(curr_gpt_response, prompt=prompt): 
                return func_clean_up(curr_gpt_response, prompt=prompt)
    return fail_safe_response


    
def llm_formated_safe_generate(prompt, 
                                example_output,
                                special_instruction,
                                repeat=3,
                                fail_safe_response="error",
                                func_validate=None,
                                func_clean_up=None,
                                verbose=False): 
    """ 
    LLM safe generate response with format instructions.
    
    special_instruction example: 
        "The output should ONLY contain ONE integer value on the scale of 1 to 10." 
        
    Output format specified as: 
        {"output": "..."}
    """
    # prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
    prompt = '"""\n' + prompt + '\n"""\n'
    prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    prompt += "Example output json:\n"
    prompt += '{"output": "' + str(example_output) + '"}'

    if verbose: 
        print ("CHAT GPT PROMPT")
        print (prompt)

    for i in range(repeat): 
        try: 
            curr_gpt_response = llm_generate(prompt).strip()
            curr_gpt_response = extract_json_from_string(curr_gpt_response)
            if verbose: 
                print ("---- repeat count: \n", i)
                print (curr_gpt_response)
                print ("~~~~")
            curr_gpt_response = curr_gpt_response["output"]
            if func_validate and func_clean_up:  # if func_validate and func_clean_up are provided, use them
                if func_validate(curr_gpt_response, prompt=prompt): 
                    return func_clean_up(curr_gpt_response, prompt=prompt)
        except: 
            pass
    return False




def print_run_prompts(prompt_template=None, 
                    persona=None, 
                    gpt_param=None, 
                    prompt_input=None,
                    prompt=None, 
                    output=None): 
    print (f"=== {prompt_template}")
    print ("~~~ persona    ---------------------------------------------------")
    print (persona.name, "\n")
    print ("~~~ gpt_param ----------------------------------------------------")
    print (gpt_param, "\n")
    print ("~~~ prompt_input    ----------------------------------------------")
    print (prompt_input, "\n")
    print ("~~~ prompt    ----------------------------------------------------")
    print (prompt, "\n")
    print ("~~~ output    ----------------------------------------------------")
    print (output, "\n") 
    print ("=== END ==========================================================")
    print ("\n\n\n")
    
    




if __name__ == '__main__':
    gpt_parameter = {"engine": "text-davinci-003", "max_tokens": 50, 
                                     "temperature": 0, "top_p": 1, "stream": False,
                                     "frequency_penalty": 0, "presence_penalty": 0, 
                                     "stop": ['"']}
    curr_input = ["driving to a friend's house"]
    prompt_lib_file = "gatsim/agent/chat_modules/prompt_templates/test_prompt.txt"
    prompt = generate_prompt(curr_input, prompt_lib_file)

    def __func_validate(gpt_response, prompt=""): 
        if len(gpt_response.strip()) <= 1:
            return False
        return True
    def __func_clean_up(gpt_response, prompt=""):
        cleaned_response = gpt_response.strip()
        return cleaned_response

    output = llm_safe_generate(prompt, 
                                gpt_parameter,
                                5,
                                "rest",
                                __func_validate,
                                __func_clean_up,
                                True)
    print(output)
    