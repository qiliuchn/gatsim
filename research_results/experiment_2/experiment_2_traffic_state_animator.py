""" 
Animation of traffic state for experiment 2.

Note: move this script to project root directory to run!




Axes Coordinates:
(0,1)        (1,1)
  +------------+
  |            |
  |  Text      |
  |            |
  +------------+
(0,0)        (1,0)

Note: transform=ax.transAxes means that the coordinates are relative to the axes, not the figure.

Figure origin is actually top left corner. Flip y-axis to make origin at bottom left!
"""

import os
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from gatsim.map.maze import Maze
from collections import defaultdict

def get_color_from_volume(link_type, volume):
    if link_type == "metro":
        return (0.5, 0.5, 0.5)  # royal blue
    
    if volume == 0:
        return (0.0, 0.5, 0.0)  # green
    elif volume == 1:
        return (0.678, 1.0, 0.184)  # greenyellow
    elif volume == 2:
        return (1.0, 1.0, 0.0)  # yellow
    elif volume == 3:
        return (1.0, 0.498, 0.314)  # coral
    elif volume == 4:
        return (1.0, 0.0, 0.0)  # red
    elif volume == 5:
        return (1.0, 0.0, 1.0)  # magenta
    elif volume >= 6:
        return (0.502, 0.0, 0.502)  # purple


def load_movement_data(folder, steps=None):
    if not steps:
        steps = sorted([int(f.split(".")[0]) for f in os.listdir(folder) if f.endswith(".json")])
    step_data = {}
    step_time = {}
    for step in steps:
        with open(os.path.join(folder, f"{step}.json")) as f:
            step_json = json.load(f)

        link_volumes = defaultdict(int)
        node_volumes = defaultdict(int)
        facility_volumes = defaultdict(int)

        queues = step_json.get("queues", {})
        for place, qtypes in queues.items():
            for qname, plist in qtypes.items():
                n = len(plist)
                if place in maze.links_info:
                    link_type = maze.links_info[place]["type"]
                    if link_type == "road" and qname in ["driving", "walking", "waiting"]:
                        link_volumes[place] += n
                    elif link_type == "metro" and qname in ["riding", "waiting"]:
                        link_volumes[place] += n
                elif place in maze.nodes_info:
                    if qname == "waiting":
                        node_volumes[place] += n
                elif place in maze.facilities_info:
                    if qname in ["staying", "waiting"]:
                        facility_volumes[place] += n

        step_data[step] = {
            "link_volumes": link_volumes,
            "node_volumes": node_volumes,
            "facility_volumes": facility_volumes,
            "curr_time": step_json.get("meta", {}).get("curr_time", "")
        }
    return step_data


def draw_maze(maze, ax):
    for link_id, link_info in maze.links_info.items():
        node1, node2 = link_info['endpoints']
        x0, y0 = maze.nodes_info[node1]['coord']
        x1, y1 = maze.nodes_info[node2]['coord']
        color = 'blue' if link_info['type'] == 'road' else 'purple'
        ax.plot([x0, x1], [y0, y1], color='green', linewidth=1, zorder=1)

    '''
    for node_id in maze.nodes_info:
        x, y = maze.nodes_info[node_id]['coord']
        ax.scatter(x, y, s=10, c='black', zorder=2)
        ax.text(x + 0.2, y + 0.2, str(node_id), fontsize=12, color='black')
    '''
    
    for fac_name, fac_info in maze.facilities_info.items():
        x, y = fac_info['coord']
        ax.scatter(x, y, s=20, c='black', marker='s', zorder=3)
        ax.text(x + 0.3, y + 0.3, fac_name, fontsize=12, color='black')


def run_visualization(sim_name, root_dir, steps=None):
    global maze
    maze = Maze("the town")
    movement_dir = os.path.join(root_dir, sim_name, "movements")
    step_data = load_movement_data(movement_dir, steps)

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.invert_yaxis()
    draw_maze(maze, ax)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    step_text = ax.text(0.00, 0.2, '', transform=ax.transAxes, fontsize=14, verticalalignment='top')
    time_text = ax.text(0.00, 0.16, '', transform=ax.transAxes, fontsize=14, verticalalignment='top')

    link_patches = []
    link_labels = {}
    for link_id, link_info in maze.links_info.items():
        node1, node2 = link_info['endpoints']
        x0, y0 = maze.nodes_info[node1]['coord']
        x1, y1 = maze.nodes_info[node2]['coord']
        if maze.links_info[link_id]['type'] == 'road':
            line, = ax.plot([x0, x1], [y0, y1], linewidth=3, color='black')
            label = ax.text((x0 + x1)/2 + 0.8, (y0 + y1)/2 + 0.8, '', fontsize=12, color='green')
        else:
            line, = ax.plot([x0 + 0.5, x1 + 0.5], [y0 - 0.5, y1 - 0.5], linewidth=3, color='gray')
            label = ax.text((x0 + x1)/2 + 0.8, (y0 + y1)/2 - 0.8, '', fontsize=12, color='gray')
        link_patches.append((link_id, line))
        link_labels[link_id] = label

    '''
    node_labels = {
        node_id: ax.text(x + 0.5, y - 0.6, '', fontsize=12, color='black')
        for node_id, data in maze.nodes_info.items()
        for x, y in [data['coord']]
    }
    '''

    facility_labels = {
        name: ax.text(x + 0.5, y - 0.6, '', fontsize=12, color='black')
        for name, data in maze.facilities_info.items()
        for x, y in [data['coord']]
    }

    def init():
        for _, line in link_patches:
            line.set_color('blue')
        for label in link_labels.values():
            label.set_text('')
        '''
        for label in node_labels.values():
            label.set_text('')
        '''
        for label in facility_labels.values():
            label.set_text('')
        step_text.set_text('Step: 0')
        time_text.set_text('Time:')
        return [line for _, line in link_patches] + list(link_labels.values()) \
            + list(facility_labels.values()) + [step_text, time_text]
        #+ list(node_labels.values()) \

    def update(frame):
        movement = step_data.get(frame, {})

        for link_id, line in link_patches:
            volume = movement.get("link_volumes", {}).get(link_id, 0)
            link_type = maze.links_info[link_id]["type"]
            line.set_color(get_color_from_volume(link_type, volume))
            link_labels[link_id].set_text(str(volume))

        '''
        for node_id in node_labels:
            volume = movement.get("node_volumes", {}).get(node_id, 0)
            node_labels[node_id].set_text(str(volume))
        '''
        
        for fac_name in facility_labels:
            volume = movement.get("facility_volumes", {}).get(fac_name, 0)
            facility_labels[fac_name].set_text(str(volume))

        step_text.set_text(f"Step: {frame}")
        time_str = movement.get("curr_time", "")
        time_text.set_text(f"Time: {time_str}")
        return [line for _, line in link_patches] + list(link_labels.values()) + \
               list(facility_labels.values()) + [step_text, time_text]  #list(node_labels.values()) + 

    ani = animation.FuncAnimation(
        fig, update, frames=sorted(step_data.keys()), init_func=init,
        blit=True, interval=200, repeat=False
    )
    plt.show()


# mobility_visualizer/main.py
sim_name = "experiment_2"
root_dir = "gatsim/storage"
one_day = 1440
morning_6_to_10 = list(range(360, 541))
#steps = morning_6_to_10 + [i + one_day for i in morning_6_to_10] + [i + one_day * 2 for i in morning_6_to_10]
steps = list(range(360, 4000))
run_visualization(sim_name, root_dir, steps)
