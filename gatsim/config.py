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
simulation_description = """You are participating in an agent-based urban mobility simulation designed to model realistic travel behavior and activity patterns in a small urban area. This simulation employs an activity-based modeling approach, which captures the complex interdependencies between daily activities, travel decisions, and urban dynamics.


-----SIMULATION FRAMEWORK-----
The simulation models how individuals plan and execute their daily activities, make travel decisions, and adapt to changing conditions. Key behavioral dimensions include:
- Activity scheduling and prioritization (work, education, shopping, leisure)
- Mode choice decisions (driving, public transit, walking)
- Route selection and timing optimization
- Response to unexpected events and system disruptions


-----URBAN ENVIRONMENT-----
The simulated town features:
- **Road Network**: Interconnected road segments with capacity constraints and dynamic travel times that respond to congestion
- **Public Transit**: A 24-hour metro system with defined routes, stations, headways, and vehicle capacities
- **Activity Locations**: Various facilities including Office, School, Factory, and recreational venues, each with capacity limitations
- **Dynamic Events**: System disruptions such as accidents, road maintenance, extreme weather events, and other incidents that affect network performance


-----AGENT ROLE-----
You will embody a specific resident of this town, making decisions based on:
- Your assigned socio-demographic profile and personal constraints
- Your activity obligations and preferences
- Your knowledge of the transportation system
- Your past experiences and learned behaviors

Your responses should reflect realistic human decision-making, considering factors such as travel time, cost, comfort, reliability, personal preferences, family needs. You will perceive the current state of the transportation system, recall relevant past experiences, and make contextually appropriate choices.

The following sections will detail the current state of the urban environment, your specific character profile, and the immediate decision context."""

# Map settings
maze_name = "the town"
maze_assets_loc = "gatsim/map"
walk_time_factor = 2  # walking over a road link takes: walk_time_factor * {link travel time}


# Agent settings
agent_path = "gatsim/agent"
# perceive
vision_r = 10  # vision radius; how far the persona can see around them.
spatial_att_bandwidth = 5  # spatial attention bandwidth for long term memory; the maximum number of nearby spatial events the agent can pay attention to in a single step. 
social_att_bandwidth = 5  # social attention bandwidth for long term memory; the maximum number of friends events the agent can pay attention to in a single step. 
# If there are more events than this limit within the agent’s vision range, the agent will only attend to the closest 
# spatial_att_bandwidth events and ignore the rest for that step. This models a cognitive constraint: even if many things are happening 
# around the agent, it can only focus on a limited subset.
retention = 6  # it’s the “window” of recent events the persona perception 
# If an event is older than the retention period (or if it’s not in that recent set), the agent treats it as a newly perceived event and stores it again in memory.
# This helps prevent repeated “re-perception” of the exact same event at every step if it’s still going on. Essentially, retention acts like a short-term “recent memory” cutoff.
min_reflect_every = 30  # at most reflect for every #min_reflect_every minutes if not "none"; default: 20; 
min_work_reflect_every = 150  # at most reflect for every #min_work_reflect_every minutes if not "none" at work place; default: 120; 

# memory params
# concept node expiration settings
# min_hours: minimum hours to expire a concept node
# max_hours: maximum hours to expire a concept node
# power: the power of the expiration function
EXPIRATION_CONFIG = {
    "event": {"min_hours": 2, "max_hours": 96, "power": 2.4},  # 4 days at most
    "chat": {"min_hours": 4, "max_hours": 48, "power": 3.2},  # 2 days at most
    "thought": {"min_hours": 8, "max_hours": 192, "power": 1.6}  # 8 days at most
}
max_extension_times = 3
lt_mem_max_size = 500  # long-term memory size

# retrieve params
relevance_weight = 0.4  # weight factor for relevance.
importance_weight = 0.3  # weight factor for importance
recency_weight = 0.3  # weight factor for how much recentness (how new a memory or event is) matters in retrieval
recency_decay = 0.74  # This variable determines how much recent memories decay over time. With a decay rate of 0.99, memories lose their recency slightly over time
keyword_weight = 1
similarity_weight = 1
spatial_temporal_weight = 1

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
# Put your name
client = OpenAI(
    # Qwen API Key
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
model_name = 'qwen-plus-latest'  
# 'qwen-max-latest' has best performance (less error, better instruction following); but very slow;
# 'qwen-plus-latest' model with best trade-off
# 'qwen-turbo-latest' quickest; but too many errors in activity plan making;
stream = False  # True for QwQ model
model_name_text_embedding = "text-embedding-v3"
#gpt_param = {"engine": "text-davinci-003", "max_tokens": 500, 
#                            "temperature": 1, "top_p": 1, "stream": False,
#                            "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
max_num_retries = 5  # max number of retries for LLM calls

# parallel computation settings
concurrent_call = True
max_planning_threads = 10  # max number of personas planning at the same time; adjust based on your system and API limits
planning_timeout = 300  # timeout for each persona planning call
import threading
lock = threading.RLock()  # used to store the lock; so that functions like pretty_print can use the lock easily. This lock will be overridden at the creation of the backend server.

# Other settings
simulation_storage = "gatsim/storage"  # persona data are saved at this folder
simulation_cache = "gatsim/cache"  # simulation temp data (like current simulation name, current step) are kept in this folder.
debug = True  # Set to True to print debug messages
output_redirect_to_file = True  # Set to True to output to file
redirect_file = "terminal_output.txt"


# LLM as a judge
judge_client = OpenAI(                       # nothing else is required
    api_key=os.getenv("OPENAI_API_KEY")
    # base_url="https://api.openai.com/v1"  # leave blank unless you’re pointing at Azure or a proxy
)
judge_model_name = 'o3'