# GATSim: Generative-Agent Transport Simulation

## Introduction
Agent is a generative agent that can perceive the surroundings and interact with the family members and friends, and schedule activity plans, and take actions.

Agent has the following modules:
 - perceive
 - memory (long term memory/ short term memory)
 - reflect
 - plan
 - act


## Setup environment
Create conda environments:

```conda create -n gatsim python=3.9 -y```

Install dependencies:

```pip install -r requirements.txt```

Install the package:

```pip install -e .```

This project uses Qwen max model with OPENAI chat completions API.

Setup LLM API key:

create .env file in the project root directory. Add the following line to the .env file:

```DASHSCOPE_API_KEY=[your qwen api key]```


Other models can be used as well. Especially, if you want to switch to ChatGPT, you can directly modify the following code in GATSIM/config.py:

```
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```



## Quick start
A backend and web UI for the simulation are provided.



### Run web UI
How to run the web UI:

First, change directory to the project root ```GATSIM/```. Then run

```python run_frontend.py runserver```

Then you can visit the web UI at ```http://127.0.0.1:8000/```

![webui img1](assets/webui1.png)
![webui img2](assets/webui2.png)


### Run backend
If you only need the simulation results.  Run the backend server:

First, change directory to the project root ```GATSIM/```. Then run
```python run_backend.py```

![backend](assets/backend1.png)
