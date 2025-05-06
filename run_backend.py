from datetime import datetime
from gatsim.backend import BackendServer
from gatsim.utils import pretty_print

opening = """
  ____    _  _____ ____  _           
 / ___|  / \|_   _/ ___|(_)_ __ ___  
| |  _  / _ \ | | \___ \| | '_ ` _ \ 
| |_| |/ ___ \| |  ___) | | | | | | |
 \____/_/   \_\_| |____/|_|_| |_| |_|
"""
print(opening)
print("=======================================Generative-Agent Transport Simulation (GATSim)========================================")

default_fork = "base_the_town"
fork_name = input(f"Enter the name of the forked simulation: (default: {default_fork}); type 'none' for creating a new simulation\n").strip()
if not fork_name:  # If user just presses Enter (empty string)
    fork_name = default_fork  # Set to default value
elif fork_name.lower() == "none":
    fork_name = None

if fork_name:
    print(f">>> Using simulation fork name: {fork_name}")
else:
    print(f">>> Creating new simulation...")

# Generate default name based on current date and time 
# Example output: "mar_19_1602"
default_simulation_name = "sim_" + datetime.now().strftime("%m%d_%H%M")
# default name: "mar_19_1602" where "1602" is HH:MM
simulation_name = input(f"\nEnter the name of this simulation run: ({default_simulation_name})\n").strip()
# Use default if user just presses Enter
if not simulation_name:
    simulation_name = default_simulation_name
    print(f">>> Using simulation name: {simulation_name}")

# create backend
backend = BackendServer(fork_name, simulation_name)

# print simulation info
# Get list of personas and facilities
persona_names = list(backend.population.keys())
pretty_print(f"Initialized {len(persona_names)} personas", 1)

facilities = list(backend.maze.facilities_info.keys())
pretty_print(f"Available facilities: {len(facilities)}", 1)
print()

# Print initial state
pretty_print("\nInitial State:", 1)
for persona_name in persona_names:
    home_facility = backend.population[persona_name].st_mem.curr_place
    pretty_print(f"{persona_name} is at {home_facility}", 2)
print()

# run simulation
backend.open_server()

# Print final state after simulation run
print("\nFinal State:")
for persona_name in persona_names:
    location = backend.population[persona_name].st_mem.curr_place 
    destination = backend.population[persona_name].st_mem.activity_facility if hasattr(backend.population[persona_name].st_mem, "activity_facility") else "No destination"
    print(f"  {persona_name} is at {location}, destination: {destination}")

# Save final state
backend.save()
print("\nSimulation test completed and state saved.")

# Enter interactive mode if needed
enter_interactive = input("Enter interactive mode? (y/n): ").strip().lower()
if enter_interactive == 'y':
    print("Entering interactive mode. Type 'help' for available commands.")
    backend.open_server()
else:
    print("Test completed. Exiting.")