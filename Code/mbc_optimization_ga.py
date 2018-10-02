# -*- coding: utf-8 -*-
"""
Created on Mon Aug  6 21:35:20 2018

@author: Hail
"""

""" 
-------------------------------------------------------------------------------
-------- FUNCTIONS ------------------------------------------------------------
-------------------------------------------------------------------------------
"""
def evaluate(individual,fin_list):
    uparams = individual[:7]
    dparams = individual[7:10]
    setpts = individual[10:13]
    
    model = swmm.swmmINP(fin_list[0])
    model.set_dicts()
    model.set_geo_dicts()
    
    offset = -479.755 # To Detroit datum
    control = True
    control_step = 0 # seconds between action
    
    ControlPoints = swmm.make_control_points(fin_list[1])
    DownstreamPoints = swmm.make_downstream_points(fin_list[3])
    
    for c,i in zip(ControlPoints,uparams):
        c.get_model_info(model)
        c.u_param = float(i)
    for d,i,j in zip(DownstreamPoints,dparams,setpts):
        d.get_model_info(model)
        d.epsilon = float(i)
        d.set_point = float(j)
        
    for d in DownstreamPoints:
        if d.d_type == 'link':
            pass
        else:
            d.dmi['q_full'] = d.max_depth
    
    
    with Simulation(fin_list[0]) as sim:
        run = swmm.system(sim,offset = offset, control = control, control_step = control_step) # Offset = 0, by default
        run.timestep = model.options['ROUTING_STEP']
        
        links = Links(sim)
        
        nodes = Nodes(sim)
        outfalls = [node for node in nodes if node.is_outfall() == True and node.nodeid != '100' and node.nodeid != '200']
        cso = []

        run.groups = max(d.group for d in DownstreamPoints)

        for c in ControlPoints:
            c.set_vars(nodes,links)
        for d in DownstreamPoints:
            d.set_vars(nodes,links)


        # DO ONCE
        for d in DownstreamPoints:
            run.group_lookup[d.group] = d.d_type
        run.group_lookup

        n = len(ControlPoints)
        link_mask = np.zeros((1,n))
        storage_mask = np.zeros((1,n))
        for c,i in zip(ControlPoints,range(0,n)):
            if run.group_lookup[c.group] == 'link':
                link_mask[0,i] = 1.0
            elif run.group_lookup[c.group] == 'storage':
                storage_mask[0,i] = 1.0
            else:
                print('Check out', c.c_name, 'neither link nor storage')

        # make group matrix. dimensions of matrix are [ # of groups , # of Control Elements ]
        # Put 1 in row if Control Element is part of group
        groupM = np.zeros((run.groups,n))
        for c,i in zip(ControlPoints,range(0,n)):
            groupM[c.group-1,i] = 1

        # Make arrays for price calculations
        uparam = np.array([c.u_param for c in ControlPoints])
        dparam = np.array([d.epsilon for d in DownstreamPoints]) # Do Once
        setpts = np.array([d.set_point for d in DownstreamPoints]) # Do Once
        n_tanks_1 = np.sum(groupM,axis=1)+1 # Do once
#        q_goals = [c.q_goal for c in ControlPoints]
        q_full = [d.dmi['q_full'] for d in DownstreamPoints]
        max_depth = np.array([d.max_depth for d in DownstreamPoints])
        set_and_full = setpts * q_full # Do once.


        run.last_action = sim.start_time
        
        print('Running Simulation... ')
        for step in sim:
            # Calculate Overflows
            cso = cso + [out.total_inflow for out in outfalls]
            
            take_action = False
            b = sim.current_time - run.last_action
            if b.total_seconds() >= run.control_step:
                take_action = True
            
            if run.control and take_action:
                run.last_action = sim.current_time
                
                ustream = np.array([c.u_var.depth / c.max_depth for c in ControlPoints])
                Uprods = uparam*ustream
                # Sum of Uparam*Ustream for each group
                np.mat(Uprods)*np.mat(groupM).transpose()

                dstream = np.array([d.d_var.depth / d.max_depth for i in DownstreamPoints])
                d_calcs = ( dstream -setpts ) * dparam # If dstream > set, P increases

                # Pareto Price for each market
                P = (np.mat(Uprods)*np.mat(groupM).transpose() + d_calcs)/ n_tanks_1
                # Give pareto price of respective group to all elements
                Pmat = np.mat(P) * np.mat(groupM)
                # Calculate individual element demands
                Pdemand = -Pmat + Uprods
                Pdemand[Pdemand < 0] = 0
                # Supply for each group
                PS = Pdemand * np.mat(groupM).transpose()

                # q_goal if all were links
                check_zero = np.divide(set_and_full, PS, out=np.zeros_like(PS), where=PS!=0)
                q_links = np.array(check_zero * groupM )* np.array( Pdemand )

                # q_goal if all were storages
                q_storage = np.array(Pdemand) * np.array( np.mat(max_depth/run.timestep) * groupM )

                # Apply masks and add together for final q_goals
                q_links = q_links * link_mask
                q_storage = q_storage * storage_mask
                q_goal = q_links + q_storage

                # Assign and send
                for q,c in zip(np.ndenumerate(q_goal),ControlPoints):
                    c.q_goal = q[1] # q is a tuple with [0] index of array and [1] the value
                    c.get_target_setting(run,nodes,links)

    
    run.flood_count = sum(c.flood_count for c in ControlPoints)
    tot_flow = sum(cso)
    
    return (run.flood_count,tot_flow)

""" 
-------------------------------------------------------------------------------
--------- FUNCTIONS END -------------------------------------------------------
-------------------------------------------------------------------------------
"""



# DEAP DEPENDENCIES
import random

from deap import base
from deap import creator
from deap import tools

# MBC/SWMM DEPENDENCIES
#from collections import OrderedDict
import swmmAPI_v2 as swmm
from pyswmm import Simulation, Links, Nodes
import numpy as np

## Start the work
IND_SIZE = 13
POP_SIZE = 12
KEEP_SIZE = 6
N_GEN = 12

fin_list = [
    'YOUR_INPUT_FILE_HERE.inp',
    'input_files/ControlPoints.csv',
    'input_files/GAP.csv',
    'input_files/DownstreamPoints.csv',
    'OUTPUT_FILE_NAME.p'
]


# weights = (-1.0,-1.0) means that we are minimizing two things of equal weight for our evaluation
creator.create("FitnessMin", base.Fitness, weights=(-1.0,-1.0))
creator.create("Individual",list,fitness=creator.FitnessMin)

toolbox = base.Toolbox()
toolbox.register("attr_float",random.random)
#toolbox.register("attr_float",random.randrange, 0, 101) # range from 0 to 100
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_float, n=IND_SIZE)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Create population made of individuals defined above
# Initialize Generation 0.
pop = toolbox.population(n=POP_SIZE)


# Evaluate Generation 0
for p in pop:
    p.fitness.values = evaluate(p,fin_list)

HoF = tools.HallOfFame(36)
HoF.update(pop)

best = tools.selBest(pop,1)
print('Best seeded outcome:')
print(best[0].fitness.values)

for i in range(N_GEN):
    print('Start Gen: ', str(i), '...')
    # Define new population
    pop_new = toolbox.population(n=0)

    winners = tools.selBest(pop,int(POP_SIZE*0.25)) # Keep 25% best in population
    rand = tools.selRandom(pop,int(POP_SIZE*0.5)) # randomly select 50% to crossover
    new = toolbox.population(n=int(POP_SIZE*0.25)) # introduce 25% of new randomness into population
    
#     print(len(winners))
#     print(len(rand))
#     print(len(new))
    
    # SELECT WINNERS
    winners = toolbox.clone(winners)
    for w in winners:
        del w.fitness.values
        mutant = toolbox.clone(w)
        mutant = tools.mutGaussian(mutant,mu=0.0, sigma=0.1, indpb = 0.2)
        pop_new.append(mutant[0])

    # SELECT RANDOM AND CROSSOVER
    rand = toolbox.clone(rand)
    for r in rand:
        del r.fitness.values
    rand1 = rand[:int((POP_SIZE*0.5)/2)]
    rand2 = rand[int((POP_SIZE*0.5)/2):]
    for r1,r2 in zip(rand1,rand2):
        child1,child2 = tools.cxUniform(r1,r2,0.25)

        pop_new.append(child1)
        pop_new.append(child2)

    for n in new:
        pop_new.append(n)
        
    
    for p in pop_new:
        if not p.fitness.values:
            p.fitness.values = evaluate(p,fin_list)
    
    pop[:] = pop_new
    HoF.update(pop)
    
    del pop_new

# Save Hall of Fame
import pickle
with open(fin_list[4],'wb') as f:
    fill = {}
    for h in HoF:
        fill[h.fitness.values] = h[:]
    pickle.dump(fill,f)