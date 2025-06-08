import networkx as nx
import os
import copy
from pacti.contracts import PropositionalIoContract
from pacti.iocontract import Var
from pacti.terms.propositions.propositions import PropositionalTerm
from pacti.terms.propositions.propositions import _expr_to_str
from alice_helperfunctions import build_composition_graph, connect_graphs, check_guarantee, plot_graph
from system_trace import get_system_trace, get_internal_system_trace

def print_graph(G, filename, graphstr, contracts, system_level=False):
    G_agr = nx.nx_agraph.to_agraph(G)
    # Set left-to-right layout
    G_agr.graph_attr["rankdir"] = "LR"
    G_agr.node_attr['style'] = 'filled'
    G_agr.node_attr['gradientangle'] = 90

    for i in G_agr.nodes():
        n = G_agr.get_node(i)
        n.attr['shape'] = 'box'
        n.attr['fillcolor'] = '#ffffff'  # default color white
        n.attr['alpha'] = 0.6
        if n.attr['type'] == 'assumption':
            n.attr['fillcolor'] = '#ffb000'
        elif n.attr['type'] == 'guarantee':
            n.attr['fillcolor'] = '#648fff'

    # Align inputs and outputs using subgraphs
    inputs = [i for i in G_agr.nodes() if G_agr.get_node(i).attr["input"] == "True"]
    outputs = [i for i in G_agr.nodes() if G_agr.get_node(i).attr["output"] == "True"]

    if inputs:
        sg_in = G_agr.add_subgraph(inputs, name="cluster_inputs")
        sg_in.graph_attr["rank"] = "same"

    if outputs:
        sg_out = G_agr.add_subgraph(outputs, name="cluster_outputs")
        sg_out.graph_attr["rank"] = "same"

    if not os.path.exists("imgs"):
        os.makedirs("imgs")
    G_agr.draw("imgs/"+filename+".pdf", prog='dot')

    return G_agr

def guarantee_generator(clist, timestep):
    """
    Generate a list of guarantees for Alice's planning component.
    """
    guarantees = []

    # for no changing cars, q has to stay the same
    status = ''
    for cx in clist:
        status += f'({cx}_t{timestep} <=> {cx}_t{timestep-1}) & '
    status = status[:-2]  # remove last '&'
    for q in [1,2,3,4]:
        guarantees.append(f'{status} & q_{q}_t{timestep-1} => q_{q}_t{timestep}')
    
    # guarantee generator for one changing car
    for c in clist:
        status = f'(~{c}_t{timestep} & {c}_t{timestep-1})'
        for cx in clist:
            if cx != c:
                status += f' & ({cx}_t{timestep} <=> {cx}_t{timestep-1})'
        for q in [2,3,4]:
            guarantees.append(f'{status} & q_{q}_t{timestep-1} => q_{q-1}_t{timestep}')

    # guarantee generator for two changing cars
    for c in clist:
        status = f'({c}_t{timestep} <=> {c}_t{timestep-1})'
        for cx in clist:
            if cx != c:
                status += f' & (~{cx}_t{timestep} & {cx}_t{timestep-1})'
        for q in [3,4]:
            guarantees.append(f'{status} & q_{q}_t{timestep-1} => q_{q-2}_t{timestep}')

    # guarantee generator for three changing cars
    status = ''
    for c in clist:
        status += f'(~{c}_t{timestep} & {c}_t{timestep-1}) &'
    status = status[:-2]  # remove last '&'
    guarantees.append(f'{status} & q_4_t{timestep-1} => q_1_t{timestep}')
    guarantees.append(f'(q_1_t{timestep} & ~q_2_t{timestep} & ~q_3_t{timestep} & ~q_4_t{timestep}) | (~q_1_t{timestep} & q_2_t{timestep} & ~q_3_t{timestep} & ~q_4_t{timestep}) | (~q_1_t{timestep} & ~q_2_t{timestep} & q_3_t{timestep} & ~q_4_t{timestep}) | (~q_1_t{timestep} & ~q_2_t{timestep} & ~q_3_t{timestep} & q_4_t{timestep})')

    # extra guarantees (that don/t have to do with couting cars)
    for i in range(100):
        guarantees.append(f'x{i} <=> y{i}')

    return guarantees

def get_perception_contract(timestep):
    extra_perception_out_vars = ['x'+str(i) for i in range(100)]
    extra_guarantees = [f'{var}' for var in extra_perception_out_vars]
    perception = PropositionalIoContract.from_strings(
        input_vars=[f'car_l_T_t{timestep}', f'car_r_T_t{timestep}', f'car_s_T_t{timestep}', 'poor_visibility'],
        output_vars=[f'car_l_P_t{timestep}', f'car_r_P_t{timestep}', f'car_s_P_t{timestep}']+extra_perception_out_vars,
        assumptions=['~ poor_visibility'],
        guarantees=[f'car_l_T_t{timestep} <=> car_l_P_t{timestep}', f'car_s_T_t{timestep} <=> car_s_P_t{timestep}', f'car_r_T_t{timestep} <=> car_r_P_t{timestep}']+extra_guarantees,)
    return perception

def get_planner_contract(timestep):
    extra_planner_in_vars = ['x'+str(i) for i in range(100)]
    extra_planner_out_vars = ['y'+str(i) for i in range(100)]
    planner = PropositionalIoContract.from_strings(
        input_vars=[f'car_l_P_t{timestep}', f'car_r_P_t{timestep}', f'car_s_P_t{timestep}', f'car_l_P_t{timestep-1}', f'car_r_P_t{timestep-1}', f'car_s_P_t{timestep-1}', f'q_1_t{timestep-1}', f'q_2_t{timestep-1}', f'q_3_t{timestep-1}', f'q_4_t{timestep-1}']+extra_planner_in_vars,
        output_vars=[f'q_1_t{timestep}', f'q_2_t{timestep}', f'q_3_t{timestep}', f'q_4_t{timestep}']+extra_planner_out_vars,
        assumptions=[f'(q_1_t{timestep-1} & ~q_2_t{timestep-1} & ~q_3_t{timestep-1} & ~q_4_t{timestep-1}) | (~q_1_t{timestep-1} & q_2_t{timestep-1} & ~q_3_t{timestep-1} & ~q_4_t{timestep-1}) | (~q_1_t{timestep-1} & ~q_2_t{timestep-1} & q_3_t{timestep-1} & ~q_4_t{timestep-1}) | (~q_1_t{timestep-1} & ~q_2_t{timestep-1} & ~q_3_t{timestep-1} & q_4_t{timestep-1})'],
        guarantees=guarantee_generator(['car_l_P', 'car_r_P', 'car_s_P'], timestep))
    return planner

def get_tracker_contract(timestep):
    extra_tracker_in_vars = ['y'+str(i) for i in range(100)]
    extra_tracker_out_vars = ['z'+str(i)+'_'+str(timestep) for i in range(100)]
    extra_guarantees = [f'y{i} <=> {var} ' for i,var in enumerate(extra_tracker_out_vars)]
    tracker = PropositionalIoContract.from_strings(
        input_vars=[f'q_1_t{timestep}', f'q_2_t{timestep}',f'q_3_t{timestep}', f'q_4_t{timestep}', 'icy_roads']+extra_tracker_in_vars,
        output_vars=[f'v_t{timestep}']+extra_tracker_out_vars,
        assumptions=['~icy_roads'],
        guarantees=[f'q_1_t{timestep} <=> v_t{timestep}']+extra_guarantees)
    return tracker

# get contract for one timestep
def get_sys_sequenced(timestep):
    """
    Get the system contract for one timestep.
    """
    perception = get_perception_contract(timestep)
    planner = get_planner_contract(timestep)

    perception_and_planner, G1 = perception.compose_diagnostics(planner, vars_to_keep=[f'q_1_t{timestep}', f'q_2_t{timestep}', f'q_3_t{timestep}', f'q_4_t{timestep}',f'car_l_P_t{timestep}', f'car_r_P_t{timestep}', f'car_s_P_t{timestep}'])
    for i in G1.nodes():
        if i not in perception_and_planner.g.terms and i not in perception_and_planner.a.terms:
            G1.nodes[i]['output'] = False
    contractdict = {'self': f'perception_{timestep}', 'other': f'planner_{timestep}', 'composition': f'perception_and_planner_{timestep}'}
    G1_a = build_composition_graph(G1, 'a', contractdict, system_level=False)
    print_graph(G1_a, 'perception_and_planner_timestep_'+str(timestep), 'a', contractdict)

    tracker = get_tracker_contract(timestep)
    sys, G2 = perception_and_planner.compose_diagnostics(tracker, vars_to_keep = [f'q_1_t{timestep}', f'q_2_t{timestep}', f'q_3_t{timestep}', f'q_4_t{timestep}', f'car_l_P_t{timestep}', f'car_r_P_t{timestep}', f'car_s_P_t{timestep}'])
    for i in G2.nodes(): # filter out every guarantee that is dropped
        if i not in sys.g.terms and i not in sys.a.terms:
            G2.nodes[i]['output'] = False
    contractdict = {'self': f'perception_and_planner_{timestep}', 'other': f'tracker_{timestep}', 'composition': f'system_{timestep}'}
    G2_a = build_composition_graph(G2, 'b', contractdict, system_level=False)

    print_graph(G2_a, 'sys_timestep_'+str(timestep), 'b', contractdict)


    return sys, perception_and_planner, G2_a, G1_a

def get_sys_final_timestep(timestep):
    """
    Get the system contract for the last timestep (do not keep the internal q and car_P variables).
    """
    perception = get_perception_contract(timestep)
    planner = get_planner_contract(timestep)

    perception_and_planner, G1 = perception.compose_diagnostics(planner)
    for i in G1.nodes():
        if i not in perception_and_planner.g.terms and i not in perception_and_planner.a.terms:
            G1.nodes[i]['output'] = False
    contractdict = {'self': f'perception_{timestep}', 'other': f'planner_{timestep}', 'composition': f'perception_and_planner_{timestep}'}
    G1_a = build_composition_graph(G1, 'c', contractdict, system_level=False)
    print_graph(G1_a, 'perception_and_planner_final_timestep_'+str(timestep), 'c', contractdict)

    tracker = get_tracker_contract(timestep)
    sys, G2 = perception_and_planner.compose_diagnostics(tracker)
    for i in G2.nodes(): # filter out every guarantee that is dropped
        if i not in sys.g.terms and i not in sys.a.terms:
            G2.nodes[i]['output'] = False
    contractdict = {'self': f'perception_and_planner_{timestep}', 'other': f'tracker_{timestep}', 'composition': f'system_{timestep}'}
    G2_a = build_composition_graph(G2, 'd', contractdict, system_level=False)
    print_graph(G2_a, 'sys_final_timestep_'+str(timestep), 'd', contractdict)

    return sys, perception_and_planner, G2_a, G1_a


timestep = 1

# compose first timestep
sys, perception_and_planner, G2, G1 = get_sys_sequenced(timestep)
G_sys_1 = connect_graphs(G2, G1)
plot_graph(G_sys_1, 'G_sys_1')

# compose second timestep
sys2, perception_and_planner2, G2_2, G1_2 = get_sys_final_timestep(timestep+1)
G_sys_2 = connect_graphs(G2_2, G1_2)
plot_graph(G_sys_2, 'G_sys_2')

# compose two timestep contracts
full_sys, G_f = sys.compose_diagnostics(sys2)
contractdict = {'self': f'system_{timestep}', 'other': f'system_{timestep+1}', 'composition': 'full_system'}
G_f = build_composition_graph(G_f, 'f', contractdict, system_level=True)
G = connect_graphs(G_f, G_sys_1, G_sys_2)
plot_graph(G, 'G')

### Now let's check the observed behavior
# get system trace
trace = get_system_trace()
behavior = {Var(key) : trace[key][0] for key in trace.keys()}
print(behavior)

sys_level_guarantee_nodes = [node for node in G.nodes() if G.nodes[node]['system_level']=='True' and G.nodes[node]['type']=='guarantee' and G.nodes[node]['output']=='True']
component_level_input_nodes = [node for node in G.nodes() if G.nodes[node]['input']=='True' and G.nodes[node]['contract'] in ['perception_1', 'planner_1', 'tracker_1', 'perception_2', 'planner_2', 'tracker_2']]

print('checking behavior')
if full_sys.a.contains_behavior(behavior):
    print('Assumptions are satisfied')
else:
    print('Assumptions are NOT satisfied')
if full_sys.g.contains_behavior(behavior):
    print('Guarantees are satisfied')
else:
    print('Guarantees are NOT satisfied')

violated_nodes = []
for i,term in enumerate(full_sys.g.terms):
    if not check_guarantee(term, behavior):
        nodes = [node for node in sys_level_guarantee_nodes if G.nodes[node]['term']==_expr_to_str(term.expression)]
        violated_node = nodes[0]
        violated_nodes.append(violated_node)
        print(f'Guarantee no. {i+1}/{len(full_sys.g.terms)}: {term} is violated by node {violated_node}')
    else:
        print(f'Guarantee no. {i+1}/{len(full_sys.g.terms)} is satisfied')
    

print(f'need to diagnose: {violated_nodes}')

to_check = []
for sink in violated_nodes:
    print(f'Checking for system_level: {sink}')
    for src in component_level_input_nodes:
        if nx.has_path(G, src, sink):
            print(f'{src} relevant')
            print(f'Need to check {G.nodes[src]["term"]} from {G.nodes[src]["contract"]}')
            if src not in to_check:
                to_check.append(src)

print(f'Have to check {len(set(to_check))/len(component_level_input_nodes)*100} % of component level inputs, {len(to_check)} out of {len(component_level_input_nodes)}')

internal_trace = get_internal_system_trace()
trace = trace | internal_trace
behavior = {Var(key) : trace[key][0] for key in trace.keys()}

for node in to_check:
    term = PropositionalTerm(G.nodes[node]['term'])
    if not check_guarantee(term, behavior):
        print(f'*** Violated Guarantee {G.nodes[node]["term"]} from {G.nodes[node]["contract"]}')
    else:
        print(f'--- Satisfied Guarantee {G.nodes[node]["term"]} from {G.nodes[node]["contract"]}')
