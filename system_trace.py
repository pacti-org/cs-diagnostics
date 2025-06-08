"""
The observed system trace for the Alice example.
"""

def get_system_trace():
    timestep = 1
    trace = {}

    # visibility and road conditions
    trace['poor_visibility'] = [0]
    trace['icy_roads'] = [0]

    # initialize the perceived cars as 1
    trace[f'car_l_P_t{timestep-1}'] = [1]
    trace[f'car_r_P_t{timestep-1}'] = [1]
    trace[f'car_s_P_t{timestep-1}'] = [1]
    # initialize as last spot in queue
    trace[f'q_1_t{timestep-1}'] = [0]
    trace[f'q_2_t{timestep-1}'] = [0]
    trace[f'q_3_t{timestep-1}'] = [0]
    trace[f'q_4_t{timestep-1}'] = [1]

    # true car observations
    trace[f'car_l_T_t{timestep}'] = [1]
    trace[f'car_r_T_t{timestep}'] = [1] 
    trace[f'car_s_T_t{timestep}'] = [1]
    trace[f'car_l_T_t{timestep+1}'] = [1]
    trace[f'car_r_T_t{timestep+1}'] = [1] 
    trace[f'car_s_T_t{timestep+1}'] = [1]

    # outputs (observable)
    # Alice's speed
    trace[f'v_t{timestep}'] = [0]
    trace[f'v_t{timestep+1}'] = [1]
    # extra tracker output vars
    for i in range(0, 100):
        trace[f'z{i}_1'] = [1]
        trace[f'z{i}_2'] = [1]

    return trace

def get_internal_system_trace():
    timestep = 1
    trace = {}
    # internal variables
    trace[f'car_l_P_t{timestep}'] = [0]
    trace[f'car_r_P_t{timestep}'] = [0]
    trace[f'car_s_P_t{timestep}'] = [0]
    trace[f'car_l_P_t{timestep+1}'] = [1]
    trace[f'car_r_P_t{timestep+1}'] = [1]
    trace[f'car_s_P_t{timestep+1}'] = [1]
    trace[f'q_1_t{timestep}'] = [0]
    trace[f'q_2_t{timestep}'] = [0]
    trace[f'q_3_t{timestep}'] = [0]
    trace[f'q_4_t{timestep}'] = [1]
    trace[f'q_1_t{timestep+1}'] = [1]
    trace[f'q_2_t{timestep+1}'] = [0]
    trace[f'q_3_t{timestep+1}'] = [0]
    trace[f'q_4_t{timestep+1}'] = [0]

    return trace
