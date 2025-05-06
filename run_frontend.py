#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.

# Introduction to frontend
The project is for transport simulation.
The frontend is a web application that allows users to visualize the transportation simulation.
The aim of the frontend is to:
    1) display the static information of the network, like facilities, nodes, links info;
    2) display the static information of the population;
    3) display the (dynamic) activity plan information of the population;
    4) visualize movements of the population on the map.
    

# Project structure
project_root/                                     # main project root
    ├── frontend/                                 # frontend (a Django project)
    │   ├── setup_backend.py                      # script handling backend argument submit on web
    │   ├── backend_wrapper.py                    # wrapper for backend to invoke backend with arguments saved  in setup_backend.py
    │   ├── frontend_server/                      # a Python package that contains Django project's core configuration files
    │   │   ├── __init__.py
    │   │   ├── settings.py                       # Frontend project settings
    │   │   ├── urls.py                           # URL routing
    │   │   ├── wsgi.py                           # WSGI application entry
    │   │   ├── asgi.py                           # ASGI application entry
    │   │   └── manage.py                         # Django management script
    │   ├── static/                               # Project-wide static files
    │   │   ├── characters/                       # character avatars
    │   │   ├── speech_bubbles/
    │   │   ├── css/
    │   │   ├── js/
    │   │   ...
    │   ├── templates/                            # Frontend project-wide templates
    │   ...
    ├── gatsim/                                   # Simulation backend, a python package
    │       ├── __init__.py
    │       ├── map/                              # store map static info
    │       │   ├── maze_meta.json                # map meta info
    │       │   |── maze.png                      # map image
    │       │   |── facilities_info.json          # facilities info
    │       │   |── nodes_info.json               # nodes info
    │       │   |── links_info.json               # links info
    │       │   ├── maze.json                     # map tiled map
    │       │   ├── maze.tsx                      # map tileset
    │       │   └── Tiles/                        # map tileset images
    │       ├── agent/                            # store population static info
    │       │   └── population_info.json
    │       ├── cache/                            # store simulation dynamic info  
    │       │   ├── curr_meta.json
    │       │   ├── curr_plans.json
    │       │   ├── curr_messages.json
    │       │   └── curr_movements.json
    │       ├── backend.py                        # backend server class file
    │       ...
    ├── run_backend.py                            # run backend serve             
    ├── run_frontend.py                           # run frontend server
    ...
    
    
frontend/ folder contains the frontend (a Django project). To run simulation, users will change directory to project_root, then run ```python run_frontend.py```.
gatsim/ folder contains the simulation backend.
Map static info is stored at gatsim/map/. Persona movements, messages are visualized on the map (gatsim/map/maze.png). 
Population static info is stored at gatsim/agent/.
Dynamic info, like simulation meta, persona movements and messages, are stored at gatsim/cache/ and updated for each simulation step.


# Layout of the web application
 - header section: display the name "GATSim" and (possible) navigation bar;
 - map section: display map and population movements on the map (left), simulation meta info like simulation name, current step, current time (upper right), and map static info (lower right, drop down menu to select the entity to display, and an area to display the entity info);
 - control section: section to place the control buttons and text input blank;
 - population section: display the static population information and dynamic plan information (display a list, one row for each persona);
 - footer section: display the developer, terms of use, and contact information.

Illustration:
+------------------------------------------------------------+
|                        GATSim                              |      header section
+------------------------------------------------------------+
|  +-------------------------------------+  +-------------+  |
|  |                                     |  |             |  |
|  |                                     |  |  Simulation |  |
|  |                                     |  |   meta info |  |
|  |                Map                  |  +-------------+  |       map section
|  |         (display movements)         |  +-------------+  |
|  |                                     |  |             |  |
|  |                                     |  |  Map static |  |
|  |                                     |  |     info    |  |
|  +-------------------------------------+  +-------------+  |
|  +------------------------------------------------------+  |
|  | [Start button] [Input text][Submit] [Stop button]    |  |       control section
|  +------------------------------------------------------+  |
|  +------------------------+  +--------------------------+  |
|  | persona_1 static info  |  | persona_1 curr plan      |  |       population section
|  +------------------------+  +--------------------------+  |
|  +------------------------+  +--------------------------+  |
|  | persona_2 static info  |  | persona_2 curr plan      |  |
|  +------------------------+  +--------------------------+  |
|  +------------------------+  +--------------------------+  |
|  | persona_3 static info  |  | persona_3 curr plan      |  |
|  +------------------------+  +--------------------------+  |
|                           ...                              |
+------------------------------------------------------------+
|        Developer | Terms of Use | Contact                  |       footer section
+------------------------------------------------------------+


# Simulation process, file update and visualization rules
Static files are not updated during simulation; dynamic files are updated by the following sequence:
 1) When a simulation step begins, simulation meta info (gatsim/cache/curr_meta.json) is updated; frontend gets the current step and time;
 2) During a simulation step, messages (gatsim/cache/curr_messages.json) and population movements (gatsim/cache/curr_movements.json) are updated; frontend moves the persons on the map, and displays the messages near the corresponding avatars on the map;
 3) At the end of a simulation step, messages are cleaned up; frontend also clears the displayed messages on the map. movements.json is not cleaned up; frontend keeps displaying the movements on the map.

 
Notes:
 1) user can start a simulation by clicking "Start" button. And there is a text box to input the fork name, simulation name, and commands. User can stop the simulation by clicking "Stop" button.
 2) Person avatars are stored at frontend/static/characters/ folder. We have avatar images for "boy", "girl", "young man", "yong woman", "old man", "old woman", with file names like "boy.png", "old women.png"
 Choose the right avatar based on the static info of the person. Age under 18 years old use "boy", age 18-50 is "young man", age 50+ is "old man".
 3) Persona location is tracked in curr_movements.json; and described in tile coordinates.
 4) When persona location is changed, frontend updates the corresponding avatar position on the map smoothly with 1 second animation.
 5) Messages are displayed in speech bubbles. The speech bubbles should be close to the avatar, and move with the avatar.
 6) Wait queue length is displayed on the map at the coordinate of each entity.
 
# File formats
## Map files (static)
gatsim/map/maze_meta.json stores meta info of the map (the maze). 
It contains the following information:
 - maze_width: width of the maze in number of tiles
 - maze_height: height of the maze in number of tiles
 - sq_tile_size: size of each square tile in pixels

Example:
{
    "maze_width": 50,
    "maze_height": 50,
    "sq_tile_size": 16
}

gatsim/map/maze.png is the background map of the simulation. It has pixel width maze_width * sq_tile_size, and pixel height maze_height * sq_tile_size.


## Population files (static)
gatsim/agent/population_info.json stores information about the population in the simulation.

Example:
{
  "Isabella Rodriguez": {
    "name": "Isabella Rodriguez",
    "gender": "female",
    "age": 34,
    "highest_level_of_education": "master's degree",
    "family_role": "single",
    "licensed_driver": true,
    "work_facility": "Coffee shop",
    "occupation": "coffee shop manager",
    "preferences_in_transportation": "prefers to drive for convenience and flexibility",
    "innate": "friendly, outgoing, hospitable, detail-oriented",
    "lifestyle": "early riser, enjoys morning yoga, works long hours, socializes with friends on weekends",
    "home_facility": "Midtown apartment",
    "household_size": 1,
    "other_family_members": [],
    "number_of_vehicles_in_family": 1,
    "household income": "middle",
    "friends": ["Sophia Nguyen"],
    "other description": "Isabella runs the town's popular coffee shop with a personal touch, knowing most regular customers by name. She attends morning yoga classes with Sophia Nguyen three times a week and hosts monthly coffee tasting events where Sophia Nguyen supplies specialty pastries."
  },
    "Sophia Nguyen": {
    "name": "Sophia Nguyen",
    "gender": "female",
    "age": 31,
    "highest_level_of_education": "master's degree",
    "family_role": "wife",
    "licensed_driver": true,
    "work_facility": "Coffee shop",
    "occupation": "barista/baker",
    "preferences_in_transportation": "cycles frequently, drives when transporting baked goods",
    "innate": "creative, perfectionist, friendly",
    "lifestyle": "early riser for baking, yoga practitioner",
    "home_facility": "Uptown apartment",
    "household_size": 2,
    "other_family_members": [
      "Daniel Nguyen"
    ],
    "number_of_vehicles_in_family": 1,
    "household income": "middle",
    "friends": ["Isabella Rodriguez"],
    "other description": "Sophia's specialty pastries have developed a cult following in town. She supplies baked goods for Isabella Rodriguez's coffee shop."
  },
    "Daniel Nguyen": {
    "name": "Daniel Nguyen",
    "gender": "male",
    "age": 32,
    "highest_level_of_education": "bachelor's degree",
    "family_role": "husband",
    "licensed_driver": true,
    "work_facility": "Office",
    "occupation": "graphic designer",
    "preferences_in_transportation": "takes metro to work, enjoys walking",
    "innate": "creative, meticulous, calm",
    "lifestyle": "photography enthusiast, home cook, minimalist",
    "home_facility": "Uptown apartment",
    "household_size": 2,
    "other_family_members": [
      "Sophia Nguyen"
    ],
    "number_of_vehicles_in_family": 1,
    "household income": "middle",
    "friends": [],
    "other description": "Daniel freelances on weekends designing logos for local businesses."
  }
}

## Simulation meta info (dynamic)
gatsim/cache/cache_meta.json stores current step meta information.
Example:
{
    "simulation_name": "sim_0503_1333",
    "curr_step": 23,
    "curr_time": "2025-03-05 13:45:00",
    "maze_name": "The town",
    "persona_names": [
        "Isabella Rodriguez",
        "Sophia Nguyen",
        "Daniel Nguyen"
    ]
}

## Plan files (dynamic)
gatsim/cache/curr_plans.json
A dict that map persona name to a list of plans.
None if no plan is available; frontend just display blank space in this case.

Example:
{
    "Isabella Rodriguez": [
            ["Uptown apartment", "06:30", "none", "none", "none", "Wake up at home, completes his morning routine."],
            ["School", "07:30", 20, "drive", "St_2, Ave_3", "Drive his daughter to school."],
            ["Coffee shop", "none", "none", "drive", "St_2, Ave_3", "Drive from School to the Coffee shop to grab a coffee before going to work."],
            ["Office", "08:20", 180, "drive", "shortest", "Go to at Office to start a day's work"],
            ["Gym", "17:30", 60, "drive", "shortest", "Go to gym to play basketball with friends."],
            ["Uptown apartment", "19:30", "none, "drive"", "shortest", "Wrap up his day by driving back home to his Uptown apartment, preparing for a restful night."]
        ]
    "Sophia Nguyen": None,
    "Daniel Nguyen": None
}
 
 
## Message files (dynamic)
gatsim/cache/curr_messages.json stores current persona messages information.
A dict that map persona name to a message (string).
None if the persona does not have a message; frontend will not display the speech bubble for this persona.

Example:
{
    "Isabella Rodriguez": "Sophia Nguyen, how about going to Gym after work today?",
    "Sophia Nguyen": "Super market area is congested. I will avoid traveling through that area.",
    "Daniel Nguyen": None
}
 
 
## Movement files (dynamic)
gatsim/cache/movements.json stores persona movements and network queues for the current step.
A dict with the following keys:
 - "meta": meta info about the simulation.
 - "mobility_events": a dict that map persona name to mobility event. One item for each persona in the simulation; recording the current mobility event of the persona.
 - "queues": one item for each entity (facility, node, link) in the network; recording the current queue list of that entity; a queue is a list of persona names.

A mobility event is a dict with the following keys:
 - "name": the name of the persona.
 - "place": the current place of the persona, facility | node | link.
 - "next_node": the next node that the persona will visit; applicable only when the persona is on a link.
 - "status": "staying" (applicable only to facility) | "waiting" | "walking" (applicable only to road links) | "riding" (applicable only to metro links) | "driving" (applicable only to road links)
 - "description": description of what the persona is doing now.
 - "coord": tile coordinates of the persona (NOT pixel coordinates!).

Example:
{
    "meta": {
        "curr_time": "2025-03-10 00:02:00"
    },
    "mobility_events": {
        "Isabella Rodriguez": {
            "name": "Isabella Rodriguez",
            "place": "Midtown apartment",
            "next_node": null,
            "status": "staying",
            "start_time": "2025-03-10 00:00:00",
            "description": "staying at home",
            "coord": [16, 12]
        },
        "Sophia Nguyen": {
            "name": "Sophia Nguyen",
            "place": "Uptown apartment",
            "next_node": null,
            "status": "staying",
            "start_time": "2025-03-10 00:00:00",
            "description": "staying at home",
            "coord": [5, 8]
        },
        "Daniel Nguyen": {
            "name": "Daniel Nguyen",
            "place": "Uptown apartment",
            "next_node": null,
            "status": "staying",
            "start_time": "2025-03-10 00:00:00",
            "description": "staying at home",
            "coord": [19, 38]
        }
    },
    "queues": {
        "Uptown apartment": {
            "staying": [
                "Sophia Nguyen",
                "Daniel Nguyen"
            ]
        },
        "Midtown apartment": {
            "staying": [
                "Isabella Rodriguez"
            ]
        },
        "Office": {},
        "Factory": {},
        "School": {},
        "Supermarket": {},
        "Hospital": {},
        "Gym": {},
        "Food court": {},
        "Coffee shop": {},
        "Amusement park": {},
        "Cinema": {},
        "Museum": {}
    }
}

"""
# The entry point for starting the Django server.
import os
import sys

def main():
    # Adjust sys.path so Django can find the project modules.
    # This adds the 'environment/frontend_server' directory to the Python path.
    project_path = 'frontend'
    sys.path.insert(0, project_path)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'frontend_server.settings')
    
    try:
        from django.core.management import execute_from_command_line
        
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?") from exc
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
