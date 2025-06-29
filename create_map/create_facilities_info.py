facilities_info = {}
facilities_info["Uptown apartment"] = {
	"coord": (14, 4),
	"description": "A residential apartment in the northwestern part of the town.",
	"base_capacity": 30,
}
facilities_info["Midtown apartment"] = {
	"coord": (2, 16),
	"description": "A residential apartment in the western part of the town.",
 	"base_capacity": 30,
}
facilities_info["Office"] = {
	"coord": (48,31),
	"description": "An office building in the town. One of the two major industries in the town.",
 	"base_capacity": 30,
}
facilities_info["Factory"] = {
	"coord": (36, 43),
	"description": "A factory in the town. One of the two major industries in the town.",
 	"base_capacity": 30,
}
facilities_info["School"] = {
	"coord": (16, 16),
	"description": "The only school in the town that enrolls both elementary and high school students.",
 	"base_capacity": 30,
}
facilities_info["Supermarket"] = {
	"coord": (27, 16),
	"description": "A supermarket in the town where you can buy household items.",
 	"base_capacity": 10,
}
facilities_info["Hospital"] = {
	"coord": (16, 27),
	"description": "The only hospital in the town.",
 	"base_capacity": 10,
}
facilities_info["Gym"] = {
	"coord": (25, 38),
	"description": "A gym where you can do various sports, such as basketball, swimming, and yoga. A good place for exercise.",
 	"base_capacity": 10,
}
facilities_info["Food court"] = {
	"coord": (36, 16),
	"description": "An open, shared seating area surrounded by multiple food vendors or kiosks. A good place for socializing and eating.",
 	"base_capacity": 10,
}
facilities_info["Coffee shop"] = {
	"coord": (38, 27),
	"description": "A nice coffee shop. A good place for socializing and drinking.",
 	"base_capacity": 10,
}
facilities_info["Amusement park"] = {
	"coord": (48, 16),
	"description": "A theme park with various entertainment facilities (such as a Ferris wheel, roller coaster, and water park. A good place for family relaxation and fun.",
 	"base_capacity": 20,
}
facilities_info["Cinema"] = {
	"coord": (27, 27),
	"description": "A cinema. A good place for relaxation and watching movies.",
 	"base_capacity": 10,
}
facilities_info["Museum"] = {
	"coord": (25, 4),
	"description": "A museum with exhibitions of various cultural, artistic, and technological artifacts. A good place for learning about history and culture, and to discover new things.",
 	"base_capacity": 10,
}


# Save to a JSON file
import json
with open("gatsim/map/facilities_info.json", "w") as file:
    json.dump(facilities_info, file, indent=4)