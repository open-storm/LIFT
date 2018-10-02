## LIFT Challenge 2018: Open-Storm Detroit Dynamics

**Team Members**
* **Wendy Barrot**, Program Director R&D, GLWA
* **Christopher Nastally**, Manager, GLWA
* **Branko Kerkez**, Assistant Professor, University of Michigan
* **Sara Troutman**, Ph.D. Student, University of Michigan
* **Abhiram Mullapudi**, Ph.D. Student, University of Michigan
* **Gregory Ewing**, Research Scientist, University of Michigan

In a collaboration between the GLWA (Great Lakes Water Authority) and Real-Time
Water Systems Lab at the University of Michigan, we investigate the application
of dynamic control to existing infrastructure in real-time to:
* Maximize current storage utilization
* Reduce combined sewer overflows
* Equalize flow to the water resources recovery facility

We aim to deliver a web-based 
[decision support dashboard](http://data.open-storm.org:3000/dashboard/snapshot/APOGoFd9HldAIICaG7l4aGZRnKwc1rtn?orgId=1) 
to be used by operators of
the sewer network during wet-weather events (see below). The tool is informed by control
algorithms developed through the LIFT Challenge.

![Decision Support Dashboard](https://github.com/kLabUM/LIFT/blob/master/DecisionSupportDashboard.PNG)

Within this repository are functions that execute the control algorithms used
to inform the decision support tool. While we do not share the underlying
GLWA system model, those interested will be able to apply the control functions
to their own system. The underlying model is an EPA SWMM input file; system
states and control actions for system assets (e.g., gate positions, pump target
settings) are accessed via [PySWMM](https://github.com/OpenWaterAnalytics/pyswmm),
a Python language SWMM wrapper.

The control algorithm employed here is Market-Based Control in which decisions
are made in a virtual marketplace where a commodity is bought and sold by
system agents. In this case, the commodity is volumetric capacity within the
sewer system, the buyers of this commodity are upstream storage agents
(e.g., pump stations, storage basins, inflatable storage dams), and the sellers
are downstream points within the sewer network, more specifically the water
resources recovery facility. The downstream point has an operator-defined
setpoint to achieve; the downstream capacity is determined as the current volume
above or below this setpoint. Price of the commodity fluctuates through time and
is based on the current state of the system: how much capacity is available and
how greatly it is demanded by upstream agents. Water is moved throughout the
system via ''purchases'' of capacity by upstream agents, which dictate how much
stored water each upstream agent can release to the downstream agents. Because
the system considered here is so large and spatially distributed, we divide the
system into sub-markets, each with its own price of capacity, one
seller/downstream agent, and potentially several buyers/upstream agents.

Each buyer/upstream agent has a particular wealth with which to ''purchase''
capacity which is based on its current volume normalized to its maximum volume
capacity; thus, if a storage agent is close to using all of its available
volume, it poses more wealth to ''purchase'' more capacity from downstream,
that is release more water to avoid flooding locally. The wealth for upstream
agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;i)
is computed via

![alt text](https://latex.codecogs.com/gif.latex?P_{wealth,i}&space;=&space;uparam_i&space;\times&space;V_{up,i})

where
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;uparam_i)
is a weighting parameter describing priority toward mitigating
local upstream flooding,
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;V_{up,i})
is the normalized volume of upstream agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;i)
.

The sum of wealth within each sub-market is computed via

![alt text](https://latex.codecogs.com/gif.latex?G_{wealth}&space;=&space;P_{wealth}&space;*&space;groupM^T)

where
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;groupM)
is a binary matrix denoting the sub-market that each upstream
agent belongs to.

Each seller/downstream agent determines the cost it places on
the commodity based on its current volume about the desired setpoint. The cost
of downstream agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
is computed as

![alt text](https://latex.codecogs.com/gif.latex?D_{cost,j}&space;=&space;\left(&space;V_{down,j}&space;-&space;setpt_{j}&space;\right)&space;\times&space;dparam_j)

where
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;V_{down,j})
is the normalized volume of downstream agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
,
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;setpt_{j})
is the operator-defined normalized volumetric setpoint of agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
, and
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;dparam)
is a weighting parameter describing priority toward achieving the setpoint.

The price of volumetric capacity within sub-market
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
is computed via

![alt text](https://latex.codecogs.com/gif.latex?p_j&space;=&space;\frac{G_{wealth,j}&space;&plus;&space;D_{cost,j}}{n_j&space;&plus;&space;1})

where
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;n_j)
is the number of buyers/upstream agents in sub-market
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
. It is crucial to note that this results in a pareto optimal distribution of
capacity for each sub-market, meaning that any benefit to one agent would result
in a detriment of other agents.

The purchasing power of each upstream agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;i)
in sub-market
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
is computed via

![alt text](https://latex.codecogs.com/gif.latex?P_{power,i}&space;=&space;\max\left(&space;P_{wealth,i}&space;-&space;p_j,&space;0&space;\right))

The available volumetric capacity in sub-market
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
is computed as

![alt text](https://latex.codecogs.com/gif.latex?V_{available,j}&space;=&space;(1-V_{down,j})&space;\times&space;V_{max,j})

where
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;V_{max,j})
is the maximum possible volume at downstream agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
.

Thus, the available flow capacity in sub-market
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;j)
is

![alt text](https://latex.codecogs.com/gif.latex?Q_{available,j}&space;=&space;\frac{V_{available,j}}{T})

where
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;T)
is the timestep of the simulation.

Finally, the flow to be released from buyer/upstream agent
![alt text](https://latex.codecogs.com/gif.latex?\inline&space;i)
is computed as

![alt text](https://latex.codecogs.com/gif.latex?Q_{goal,i}&space;=&space;Q_{available,j}&space;\times&space;P_{power,i})
