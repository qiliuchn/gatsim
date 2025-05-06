nodes_info = {}
nodes_info['Node_1'] = {
    'coord':(14,6),
    'facilities': ["Uptown apartment"],
}
nodes_info['Node_2'] = {
    'coord':(48,29),
    'facilities': ["Office"],
}
nodes_info['Node_3'] = {
    'coord':(36,40),
    'facilities': ["Factory"],
}
nodes_info['Node_4'] = {
    'coord':(2,18),
    'facilities': ["Midtown apartment"],
}
nodes_info['Node_5'] = {
    'coord':(14,18),
    'facilities': ["School"],
}
nodes_info['Node_6'] = {
    'coord':(25,18),
    'facilities': ["Supermarket"],
}
nodes_info['Node_7'] = {
    'coord':(36,18),
    'facilities': ["Food court"],
}
nodes_info['Node_8'] = {
    'coord':(48,18),
    'facilities': ["Amusement park"],
}
nodes_info['Node_9'] = {
    'coord':(14,29),
    'facilities': ["Hospital"],
}
nodes_info['Node_10'] = {
    'coord':(25,29),
    'facilities': ["Cinema"],
}
nodes_info['Node_11'] = {
    'coord':(36,29),
    'facilities': ["Coffee shop"],
}
nodes_info['Node_12'] = {
    'coord':(25,6),
    'facilities': ["Museum"],
}
nodes_info['Node_13'] = {
    'coord':(24,40),
    'facilities': ["Gym"],
}

# Save to a JSON file
import json
with open("gatsim/map/nodes_info.json", "w") as file:
    json.dump(nodes_info, file, indent=4)