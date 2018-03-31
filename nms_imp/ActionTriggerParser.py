import bpy

from classes import *

def ParseNodes():
    nodes = bpy.data.node_groups
    node_names = list()

    entityData = GcTriggerActionComponentData()     # just do default as everything there is fine and the States are intiialised as an empty List
    
    # first, go through and get all the ActionTrigger nodes in the blender file and add the names to a list
    for node in nodes:
        print(node.name)
        if node.bl_idname == 'NMSATTree':   # only add nodes trees that are the custom type
            node_names.append(node.name)

    
    for name in node_names:
        print('Processing node: {}'.format(name))
        ActionTrigger = bpy.data.node_groups[name]
        # set some intial values to be filled
        Actions = []
        Trigger = None
        Builder = None

        # now go through all the nodes in the node Tree and organise them into categories:
        for node in ActionTrigger.nodes:
            if node.bl_idname.endswith('Event'):
                Trigger = node
            else:
                # we could check, but the only other option is an action, and not all actions end with Action (looking at you DisplayText!)
                Actions.append(node)

        # we can now handle each of the types of nodes individually.
        # we know that the Trigger will have just one output, the Actions will have just one input, and the Builder will have one input and many outputs (all off the one socket)
        # we don't actually care about the inputs and ouputs though as they are just visual.

        if Trigger is not None or len(Actions) != 0:
            Trigger_struct = FillStruct(Trigger)
            Action_structs = list(FillStruct(action) for action in Actions)

            # fill the inner-most ActionTrigger struct with data
            ActionTriggerData = {'Trigger': Trigger_struct,
                                 'Action': List()}
            for action in Action_structs:
                ActionTriggerData['Action'].append(action)

            Triggers = GcActionTrigger(**ActionTriggerData)
            # next create the data for the action trigger state and add to the list of action trigger data in the outmost struct
            Data = GcActionTriggerState(StateID = name,
                                        Triggers = List(Triggers))
            entityData['States'].append(Data)

    return entityData

        

def FillStruct(node):
    # this function will get a node, and convert all the data inside it into the appropriate struct type (I hope!!)
    struct_name = 'Gc' + node.bl_idname[4:]
    cls = eval(struct_name)     # this is the actual class relating to the struct
    properties = dict()
    for prop in node.keys():
        properties[prop] = node[prop]
    return cls(**properties)


# now we need to create the actual component for the entity file

"""        Old code relating to figuring out what eack link joins (maybe needed in the future??)
# we now need to parse all the sub nodes. We will assume that there is only one action trigger per node tree
node_structure = list()     # this will be a list of dictionaries. The dictionary will contain the name of the node, the name of the input node, and the names of the output nodes
for node in ActionTrigger.nodes:
    input_node = node.inputs[0].links[0].from_node.name         # ewww... not sure if there is a better way to do this though
    output_nodes = list()
    for 
    node_structure.append({'name': node.name})
"""
