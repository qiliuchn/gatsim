# Note: 
# transit line direction 0 means the transit go from link_data['endpoints'][0] to link_data['endpoints'][1] when traveling on each transit link
# this convention should be complied when defining 1) links info; and 2) the transit schedule

links_info = {}
# Ave 1
links_info['Ave_1_link_1'] = {
    'endpoints':('Node_1', 'Node_12'),
    'type': 'road',
    'travel_time': 6,
    'wait_time': 0,
    'base_capacity': 2,
}

# Ave 2
links_info['Ave_2_link_1'] = {
    'endpoints':('Node_4', 'Node_5'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['Ave_2_link_2'] = {
    'endpoints':('Node_5', 'Node_6'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['Ave_2_link_3'] = {
    'endpoints':('Node_6', 'Node_7'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['Ave_2_link_4'] = {
    'endpoints':('Node_7', 'Node_8'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}

# Ave 3
links_info['Ave_3_link_1'] = {
    'endpoints':('Node_9', 'Node_10'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['Ave_3_link_2'] = {
    'endpoints':('Node_10', 'Node_11'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['Ave_3_link_3'] = {
    'endpoints':('Node_11', 'Node_2'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}

# Ave 4
links_info['Ave_4_link_1'] = {
    'endpoints':('Node_13', 'Node_3'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}

# St 1
links_info['St_1_link_1'] = {
    'endpoints':('Node_4', 'Node_9'),
    'type': 'road',
    'travel_time': 8,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['St_1_link_2'] = {
    'endpoints':('Node_9', 'Node_13'),
    'type': 'road',
    'travel_time': 8,
    'wait_time': 0,
    'base_capacity': 2,
}

# St 2
links_info['St_2_link_1'] = {
    'endpoints':('Node_1', 'Node_5'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['St_2_link_2'] = {
    'endpoints':('Node_5', 'Node_9'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}

# St 3
links_info['St_3_link_1'] = {
    'endpoints':('Node_12', 'Node_6'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['St_3_link_2'] = {
    'endpoints':('Node_6', 'Node_10'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}

# St 4
links_info['St_4_link_1'] = {
    'endpoints':('Node_7', 'Node_11'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['St_4_link_2'] = {
    'endpoints':('Node_11', 'Node_3'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}

# St 5
links_info['St_5_link_1'] = {
    'endpoints':('Node_12', 'Node_8'),
    'type': 'road',
    'travel_time': 18,
    'wait_time': 0,
    'base_capacity': 2,
}
links_info['St_5_link_2'] = {
    'endpoints':('Node_8', 'Node_2'),
    'type': 'road',
    'travel_time': 5,
    'wait_time': 0,
    'base_capacity': 2,
}

# metro 1
# Ave 2
links_info['Metro_1_link_1'] = {
    'endpoints':('Node_4', 'Node_5'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}
links_info['Metro_1_link_2'] = {
    'endpoints':('Node_5', 'Node_6'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}
links_info[' Metro_1_link_3'] = {
    'endpoints':('Node_6', 'Node_7'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}
links_info['Metro_1_link_4'] = {
    'endpoints':('Node_7', 'Node_8'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}

# metro 2
links_info['Metro_2_link_1'] = {
    'endpoints':('Node_12', 'Node_6'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}
links_info['Metro_2_link_2'] = {
    'endpoints':('Node_6', 'Node_10'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}
links_info['Metro_2_link_3'] = {
    'endpoints':('Node_10', 'Node_11'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}
links_info['Metro_2_link_4'] = {
    'endpoints':('Node_11', 'Node_3'),
    'type': 'metro',
    'travel_time': 5,
    'wait_time': 10,
    'base_capacity': 5,
}

# Save to a JSON file
import json
with open("gatsim/map/links_info.json", "w") as file:
    json.dump(links_info, file, indent=4)