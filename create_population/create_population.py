# population is mainly created by using LLM
# you can manually add persona by this script.
# the result will be saved to "persona_info_example.json"
population_info = {}

population_info['Isabella Rodriguez'] = {
 'gender': 'female',
 'age': 34,
 'highest_level_of_education': 'master',
 'family_role': 'single',
 'licensed_driver': True,
 'work_facility': 'Coffee shop',
 'occupation': 'barista',
 'preferences_in_transportation': 'prefer to travel alone and prefer safer way to travel; mainly drive around', 
 'innate': "friendly, outgoing, hospitable",
 'lifestyle': "Isabella Rodriguez goes to bed around 11pm, awakes up around 6am.",
 'home_facility': 'Uptown apartment',
 'household_size': 1,
 'other_family_members': [],
 'number of vehicles': 1,
 'household_income': 'medium',
 'friends': ['Jennifer Moore'],
 'other_description': 'Isabella Rodriguez is a cafe owner who loves to make people feel welcome. She is always looking for ways to make the cafe a place where people can come to relax and enjoy themselves.',
}

population_info['John Lin'] = {
 'gender': 'male',
 'age': 45,
 'highest_level_of_education': 'high school',
 'family_role': 'father',
 'licensed_driver': False,
 'work_facility': 'Factory',
 'occupation': 'worker',
 'preferences_in_transportation': 'prefer to economic and reliable ways of transportation; mainly take transit to work', 
 'innate': "patient, kind, organized",
 'lifestyle': "John Lin goes to bed around 10pm, awakes up around 6am, eats dinner around 5pm.",
 'home_facility': 'Midtown apartment',
 'household_size': 3,
 'other_family_members': ['May Lin', 'Marie Lin'],
 'number_of_vehicles_in_family': 1,
 'household_income': 'medium',
 'friends': ['Klaus Mueller'],
 'other_description': 'John Lin holds traditional values, live a healthy lifestyle, and is a good listener. He takes care of his family and children.',
}

population_info['Maria Lin'] = {
 'gender': 'female',
 'age': 10,
 'highest_level_of_education': 'None',
 'family_role': 'daughter',
 'licensed_driver': False,
 'work_facility': None,
 'occupation': 'elementary school student (5-th grade)',
 'preferences_in_transportation': 'prefer to be accompanied by parent; prefer mom to drive her to school', 
 'innate': "kind, a little bit of shy",
 'lifestyle': "Maria Lin goes to bed around 7:30 pm, awakes up around 7:00 am, eats dinner around 5pm.",
 'home_facility': 'Midtown apartment',
 'household_size': 3,
 'other_family_members': ['John Lin', 'May Lin'],
 'number_of_vehicles_in_family': 1,
 'household_income': 'medium',
 'friends': ['Hailey Johnson'],
 'other_description': 'Maria Lin is a kind, shy girl. She is very good at school and has a good GPA. She is very happy with her life.',
}

# Save to a JSON file
import json
with open("gatsim/agent/population_info_example.json", "w") as file:
    json.dump(population_info, file, indent=4)