# config.py
# configuration file for the simulation

# Simulator settings
# effective when creating a new simulation
# Note: fork simulation will inherit the settings from the original simulation
start_date = "2025-03-10 00:00:00"
# time format: YYYY-MM-DDTHH:mm:ss
# to convert string to time obj:
# datetime.strptime(config.start_date, "%Y-%m-%d %H:%M:%S")
# Convert back to string in the same format
#time_str = time_obj.strftime("%Y-%m-%d %H:%M:%S")
# day_of_week = date_obj.weekday()
# if you want the datetime string to include day of the week:
# dt.strftime("%a %Y-%m-%d %H:%M")
server_sleep = 0.1  #the amount of time that our while loop rests each cycle; this is to not kill our machine. 
maze_name = 'The town'
minutes_per_step = 1
simulation_description = """We are running an urban transport simulation program. This program is designed to simulate people's travel behavior in a small town. Activity-based approach is adopted. This encompasses the study of how people move and their choices regarding transportation, trip purposes, and frequency, influenced by factors like socio-demographics, economic conditions, and travel motivations. 
You will play the role of an agent inside this virtual town. The transportation network, the facilities of the town, as well as the socioeconomic attributes of the person you play, will be introduced below.\n"""

# Map settings
maze_assets_loc = "gatsim/map"
walk_time_factor = 4  # walking over a road link takes: walk_time_factor * {link travel time}


# Agent settings
agent_path = "gatsim/agent"
persona_storage = "gatsim/storage"  # persona data are saved at this folder
# perceive
vision_r = 10  # vision radius; how far the persona can see around them.
spatial_att_bandwidth = 3  # spatial attention bandwidth for long term memory; the maximum number of nearby spatial events the agent can pay attention to in a single step. 
social_att_bandwidth = 3  # social attention bandwidth for long term memory; the maximum number of friends events the agent can pay attention to in a single step. 
# If there are more events than this limit within the agent’s vision range, the agent will only attend to the closest 
# spatial_att_bandwidth events and ignore the rest for that step. This models a cognitive constraint: even if many things are happening 
# around the agent, it can only focus on a limited subset.
retention = 9  # it’s the “window” of recent events the persona considers as already perceived. 
# If an event is older than the retention period (or if it’s not in that recent set), the agent treats it as a newly perceived event and stores it again in memory.
# This helps prevent repeated “re-perception” of the exact same event at every step if it’s still going on. Essentially, retention acts like a short-term “recent memory” cutoff.
min_reflect_every = 30  # at most reflect for every #min_reflect_every minutes if not "none"; default: 20; 
min_work_reflect_every = 150  # at most reflect for every #min_work_reflect_every minutes if not "none" at work place; default: 120; 

# retrieve params
relevance_weight = 0.6  # weight factor for relevance.
importance_weight = 0.2  # weight factor for importance
recency_weight = 0.2  # weight factor for how much recentness (how new a memory or event is) matters in retrieval
recency_decay = 0.8  # This variable determines how much recent memories decay over time. With a decay rate of 0.99, memories lose their recency slightly over time
keyword_weight = 0.4
similarity_weight = 0.3
spatial_temporal_weight = 0.3
retrieve_recent = 2  # retrieve latest #retrieve_recent many events and #retrieve_recent chats each time

# reflect params
#importance_trigger_max = 150  # the maximum threshold for the importance level that triggers reflection. Once the importance of certain events or thoughts reaches this value, the reflection process will be activated.
# importance_trigger_curr is the current importance level that controls when the reflection process should be triggered. 
# importance_ele_n  track how many significant or important elements (like events or thoughts) the persona has encountered and processed; 
# it determines how many recent events (or thoughts) should be considered for reflection;  the persona considers the most recent importance_ele_n events or thoughts for reflection,


# chat settings
max_num_people_to_chat_with = 3  # max number of people a persona can chat with for each decision time
max_num_chat_rounds_per_conversation = 3  # max number of chat rounds for a conversation


# LLM settings
from openai import OpenAI
# Copy and paste your OpenAI API Key
import os
from dotenv import load_dotenv
load_dotenv()
openai_api_key = "sk-b0d8cd45d4a147edbcd1d3206181830e"
# Put your name
client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
model_name = 'qwen-max-latest'
model_name_text_embedding = "text-embedding-v3"
gpt_param = {"engine": "text-davinci-003", "max_tokens": 500, 
                            "temperature": 1, "top_p": 1, "stream": False,
                            "frequency_penalty": 0, "presence_penalty": 0, "stop": None}


# Other settings
cache = "gatsim/cache"  # simulation temp data (like current simulation name, current step) are kept in this folder.
debug = True  # Set to True to print debug messages
