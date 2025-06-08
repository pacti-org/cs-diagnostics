from ipdb import set_trace as st
import networkx as nx
import copy
import os
from pacti.terms.propositions.propositions import _is_tautology, _subst_var, _expr_to_str


# Check the behavior
def check_guarantee(term, behavior):
    new_expr = copy.copy(term.expression)
    for key in behavior.keys():
        new_expr = _subst_var(new_expr, key.name, behavior[key])
    return _is_tautology(new_expr)

def build_composition_graph(G, prefix, contractdict, system_level=False):
    G = nx.nx_agraph.to_agraph(G)
    outputs = [i for i in G.nodes() if G.get_node(i).attr["output"] == "True"]
    inputs = [i for i in G.nodes() if G.get_node(i).attr["input"] == "True"]
    intersection = set(inputs).intersection(set(outputs))
    internal_nodes = [i for i in G.nodes() if G.get_node(i).attr["input"] == "False" and G.get_node(i).attr["output"] == "False"]

    G_mod = nx.DiGraph()
    new_inputnodes = {}
    new_outputnodes = {}
    new_internal_nodes = {}
    for i,node in enumerate(G.nodes()):
        if node in intersection:
            # if node is both input and output, create two nodes and connect them
            G_mod.add_node(prefix+str(i)+'i', term=node, type = G.get_node(node).attr["type"], input="True", output="False", contract = contractdict[G.get_node(node).attr["component"]], system_level = system_level)
            new_inputnodes.update({node: prefix+str(i)+'i'})
            G_mod.add_node(prefix+str(i)+'o', term=node, type = G.get_node(node).attr["type"], input="False", output="True", contract =  contractdict["composition"], system_level = system_level)
            new_outputnodes.update({node: prefix+str(i)+'o'})
            G_mod.add_edge(prefix+str(i)+'i', prefix+str(i)+'o')  # connect the same terms
        elif node in inputs:
            G_mod.add_node(prefix+str(i)+'i', term=node, type = G.get_node(node).attr["type"], input="True", output="False", contract = contractdict[G.get_node(node).attr["component"]], system_level = system_level)
            new_inputnodes.update({node: prefix+str(i)+'i'})
        elif node in outputs:
            G_mod.add_node(prefix+str(i)+'o', term=node, type = G.get_node(node).attr["type"], input="False", output="True", contract = contractdict["composition"], system_level = system_level)
            new_outputnodes.update({node: prefix+str(i)+'o'})
        elif node in internal_nodes:
            G_mod.add_node(prefix+str(i), term=node, type = G.get_node(node).attr["type"], input="False", output="False", contract = "internal", system_level = system_level)
            new_internal_nodes.update({node: prefix+str(i)})
        
    for u, v in G.edges():
        if u in inputs and v in outputs:
            # connect input to output
            out_node = new_inputnodes[u]
            in_node = new_outputnodes[v]
            G_mod.add_edge(out_node, in_node)
        elif u in inputs and v in internal_nodes:
            # connect input to internal
            out_node = new_inputnodes[u]
            in_node = new_internal_nodes[v]
            G_mod.add_edge(out_node, in_node)
        elif u in internal_nodes and v in outputs:
            # connect internal to output
            out_node = new_internal_nodes[u]
            in_node = new_outputnodes[v]
            G_mod.add_edge(out_node, in_node)
        elif u in internal_nodes and v in internal_nodes:
            # connect internal to internal
            out_node = new_internal_nodes[u]
            in_node = new_internal_nodes[v]
            G_mod.add_edge(out_node, in_node)

    return G_mod

def connect_graphs(CompG, inG1, inG2 = None):
    """
    Connect a composition graph to a diagnostics graph.
    Inputs:
    CompG: Graph composing the outputs of inG1 (and inG2).
    inG1: First graph
    inG2: Second graph
    Returns:
    G: Diagnostics graph where the output of inG1 (and inG2) feeds into CompG.
    """
    from ipdb import set_trace as st  

    # create the new graph object
    G = nx.DiGraph()

    def add_nodes_and_edges(graph):
        for u in graph.nodes():
            attrs = dict(u.attr)
            G.add_node(u, **attrs)
        for edge in graph.edges():
            source = edge[0]
            target = edge[1]
            attrs = dict(edge.attr)
            G.add_edge(source, target, **attrs)

    def feed_into(ingraph, outgraph):
        # st()
        outputnodes = [ingraph.get_node(u) for u in ingraph.nodes() if ingraph.get_node(u).attr["output"] == "True"]
        inputnodes = [outgraph.get_node(v) for v in outgraph.nodes() if outgraph.get_node(v).attr["input"] == "True"]
        for u in outputnodes:
            # find the corresponding input node in G2
            for v in inputnodes:
                if ingraph.get_node(u).attr["term"] == outgraph.get_node(v).attr["term"] and ingraph.get_node(u).attr["contract"] == outgraph.get_node(v).attr["contract"]:
                    # connect them in the G graph
                    G.add_edge(u, v)
                    # set input to false for the node that was connected
                    G.nodes[u]['output'] = "False"
                    G.nodes[v]['input'] = "False"
    
    try:
        inG1 = nx.nx_agraph.to_agraph(inG1)
    except:
        pass
    try:
        CompG = nx.nx_agraph.to_agraph(CompG)
    except:
        pass

    add_nodes_and_edges(inG1)
    add_nodes_and_edges(CompG)
    feed_into(inG1, CompG)
    if inG2:
        # st()
        try:
            inG2 = nx.nx_agraph.to_agraph(inG2)
        except:
            pass
        add_nodes_and_edges(inG2)
        feed_into(inG2, CompG)
    # st()
    return G


def plot_graph(G, filename):
    G_agr = nx.nx_agraph.to_agraph(G)
    # G_agr, mapping = postprocess(G2, graphstr, contracts, system_level)
    # Set left-to-right layout
    G_agr.graph_attr["rankdir"] = "LR"
    G_agr.node_attr['style'] = 'filled'
    G_agr.node_attr['gradientangle'] = 90

    for i in G_agr.nodes():
        n = G_agr.get_node(i)
        # st()
        n.attr['shape'] = 'box'
        n.attr['fillcolor'] = '#ffffff'  # default color white
        n.attr['alpha'] = 0.6
        # n.attr['label'] = ''
        if n.attr['type'] == 'assumption':
            n.attr['fillcolor'] = '#ffb000'
        elif n.attr['type'] == 'guarantee':
            n.attr['fillcolor'] = '#648fff'

    #Align inputs and outputs using subgraphs
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