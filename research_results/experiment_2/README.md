# Experiment 2

## Introduction
This experiment examines emergent microscopic traffic patterns in a week-long simulation beginning Monday, March 10, 2025. For computational efficiency, children's mobility is not explicitly modeled; instead, their travel is incorporated into parental trip chains. Parents with school-age children must accommodate morning drop-offs and evening pick-ups within their daily schedules. The virtual population consists of 60 adults, with 37 employed at factory or office locations, predominantly working 8:00–17:00 shifts. This temporal concentration of commute demand naturally generates two traffic peaks.

We developed two analysis tools— `traffic_state_animator` and `traffic_state_snapshot`—to visualize spatiotemporal traffic evolution. Figure 2 presents traffic snapshots at 7:00, 7:30, 8:00, and 8:30 for the first three simulation days. On Monday, most agents depart around 7:20, allowing approximately 40 minutes to reach their workplace under free-flow conditions. However, the resulting congestion causes only 7 agents to arrive punctually at 8:00. 

As agents accumulate travel experiences and update their mental models through reflection, they adaptively adjust departure times, routes, and mode choices. The temporal evolution is evident in Figure 2's first column: the morning peak progressively shifts earlier from Monday to Wednesday. While the network remains uncongested at 7:00 on Monday, mild congestion emerges by Wednesday at the same hour. Concurrently, traffic disperses more broadly across the network, with a modest increase in transit ridership.

These results demonstrate that GATSim produces realistic microscopic traffic patterns through distributed agent learning, achieving traffic states comparable to traditional user equilibrium models without centralized optimization. Agents independently discover efficient departure times, routes, and modes through experience-based adaptation. The complete simulation configuration and results are available in `gatsim/storage/experiment_2`. Readers can run `experiment_2_traffic_state_animator` to view the animation.


![experiment 2](experiment_2.png)



## Notes
 - Experiment 2 simulation data are stored at gatsim/storage/experiment_2.

 - `experiment_2_ttraffic_state_snapshot.ipynb' contains the traffic state snapshots (move to root folder to run).

 - `experiment_2_traffic_state_animator.py' contains the traffic state animator (move to root folder to run).