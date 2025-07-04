# Note: 
# transit line direction 0 means the transit go from link_data['endpoints'][0] to link_data['endpoints'][1] when traveling on each transit link
# this convention should be complied when defining 1) links info; and 2) the transit schedule

import pandas as pd
from datetime import datetime, timedelta

t = 8  # transit links travel time
w = 1  # time spending at each stop; default: 1 minute

def create_transit_schedule(file_path, start_date, end_date, headway):
    """
    Create a transit schedule and save it to a CSV file.
    
    Parameters:
    file_path (str): Path where the schedule will be saved
    start_date (str): Start date and time in format "YYYY-MM-DD HH:MM:SS"
    end_date (str): End date and time in format "YYYY-MM-DD HH:MM:SS"
    headway (int): Time between services in minutes
    
    Returns:
    None: Writes schedule to the specified file path
    """
    # Convert string dates to datetime objects
    start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    
    # Define metro lines and their stops
    metro_lines = {
        "Metro_1": {
            0: ["Node_4", "Node_5", "Node_6", "Node_7", "Node_8", "Node_2"],
            1: ["Node_2", "Node_8", "Node_7", "Node_6", "Node_5", "Node_4"]
        },
        "Metro_2": {
            0: ["Node_1", "Node_12", "Node_6", "Node_10", "Node_11", "Node_3"],
            1: ["Node_3", "Node_11", "Node_10", "Node_6", "Node_12", "Node_1"]
        }
    }
    
    # Calculate time between stops based on the example
    stop_interval = {}  # minutes between stops
    stop_interval["Metro_1"] = {
        0: [t + w, t + w, t + w, t + w, t + w],
        1: [t + w, t + w, t + w, t + w, t + w]
    }
    stop_interval["Metro_2"] = {
        0: [t + w, t + w, t + w, t + w, t + w],
        1: [t + w, t + w, t + w, t + w, t + w]
    }
    
    # Initialize list to store schedule entries
    schedule = []
    
    # Generate schedule for each metro line and direction
    for metro_line, directions in metro_lines.items():
        for direction, stops in directions.items():
            current_time = start_dt
            
            # Continue generating trips until end date is reached
            while current_time <= end_dt:
                stop_time = current_time
                
                # Add entries for each stop in this trip
                for i, stop in enumerate(stops):
                    schedule.append([
                        metro_line,
                        direction,
                        stop,
                        stop_time.strftime("%Y-%m-%d %H:%M:%S")
                    ])
                    
                    # Move to the next stop time if not the last stop
                    if i < len(stops) - 1:
                        stop_time += timedelta(minutes=stop_interval[metro_line][direction][i])
                
                # Move to the next trip based on headway
                current_time += timedelta(minutes=headway)
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(schedule, columns=["metro_line", "direction", "node", "datetime"])
    df.to_csv(file_path, index=False)
    
    print(f"Transit schedule created and saved to {file_path}")
    
    
if __name__ == "__main__":
    create_transit_schedule("gatsim/map/transit_schedule.csv", "2025-03-10 00:00:00", "2025-03-17 23:59:59", 10)