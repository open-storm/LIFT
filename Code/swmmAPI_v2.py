import math
import pandas as pd
from collections import OrderedDict
from pyswmm import Simulation
import pyswmm
import numpy as np


# CLASSES
class swmmINP:
    
    def __init__(self,inpF,*args,**kwargs):
        self.inpF = inpF
        self.args = args
        self.kwargs = kwargs
        self.warnings = []

        # Handle keyword args.
        self.set_kwargs()
            
        self.make_sections()
        # self.prep_dicts() # think this should be handled if you know what headers you have
        
    # SET
    def set_kwargs(self):
        # DEFAULTS
        self.offset = 0.0
        self._min_slope = 0.0
        self.headers = ['[TITLE]','[OPTIONS]','[EVAPORATION]','[RAINGAGES]','[SUBCATCHMENTS]',
           '[SUBAREAS]','[INFILTRATION]','[JUNCTIONS]','[OUTFALLS]','[STORAGE]','[CONDUITS]',
           '[PUMPS]','[ORIFICES]','[WEIRS]','[XSECTIONS]','[LOSSES]','[CONTROLS]','[INFLOWS]',
           '[DWF]','[HYDROGRAPHS]','[RDII]','[CURVES]','[TIMESERIES]','[PATTERNS]','[REPORT]',
           '[TAGS]','[MAP]','[COORDINATES]','[VERTICES]','[Polygons]','[SYMBOLS]','[PROFILES]']
        
        kw = self.kwargs.keys()
        if 'offset' in kw:
            self.offset = self.kwargs['offset']
        
        if 'min_slope' in kw:
            self._min_slope = self.kwargs['slope']

        if 'headers' in kw:
            self.headers = self.kwargs['headers']

    def set_dicts(self):
        self.make_xsec_dict()
        self.make_curves_dictionary()
        self.make_conduit_dictionary()
        self.make_junction_dictionary()
        self.make_storage_dictionary()
        self.make_subcatchment_dictionary()
        self.make_outfall_dictionary()
        self.make_orifice_dictionary()
        self.make_pump_dictionary()
        self.make_options_dictionary()
        self.make_raingauges_dict()
        self.make_timeseries_dict()
        self.make_evap_dict()
        self.make_infiltration_dict()
        self.make_losses_dict()
        self.make_controls_dict()
        self.make_inflows_dict()


        self.calc_slope()
        self.calc_qfull()

    def set_geo_dicts(self):
        self.make_map_dict()
        self.make_coords_dict()
        self.make_verts_dict()
        self.make_polygons_dict()

    # MAKE
    def make_conduit_dictionary(self):
        self.conduits = {}
        for l in self._sections['[CONDUITS]']:
            a = l.split()

            self.conduits[a[0]] = {
                'from_node': a[1],
                'to_node': a[2],
                'length': float(a[3]),
                'roughness': float(a[4]),
                'in_offset': float(a[5]),
                'out_offset': float(a[6]),
                'init_flow': float(a[7]),
                'max_flow': float(a[8]),
            }

        for c in self.conduits:
            self.conduits[c].update(self.xsections[c])

        self.calc_conduit_vol()

    def make_controls_dict(self):
        control_list = [l for l in self._sections['[CONTROLS]']]
        self.controls = {}
        for i in control_list:
            if 'RULE' in i:
                self.controls[i.split()[1]] = []

        for i in control_list:
            if 'RULE' in i:
                rule = i.split()[1]
            else:
                self.controls[rule].append(i)

    def make_coords_dict(self):
        self.coords = {}

        for l in self._sections['[COORDINATES]']:
            a = l.split()
            self.coords[a[0]] = {
                'x': float(a[1]),
                'y': float(a[2]),
            }
        
    def make_curves_dictionary(self):
        self.curves = {}

        for l in self._sections['[CURVES]']:
            a = l.split()

            if len(a) == 4:
                self.curves[a[0]] = {
                    'type':a[1],
                    'x_val':[a[2]],
                    'y_val':[a[3]]
                }

            if len(a) == 3:
                self.curves[a[0]]['x_val'].append(a[1])
                self.curves[a[0]]['y_val'].append(a[2])
                
    def make_evap_dict(self):
        evap_raw = self._sections['[EVAPORATION]']
        self.evaporation = {
            'constant' : float(evap_raw[0].split()[1]),
            'dry_only' : evap_raw[1].split()[1]    
        }
        del evap_raw
        
    def make_infiltration_dict(self):
        self.infiltration = {}
        for l in self._sections['[INFILTRATION]']:
            a = l.split()

            self.infiltration[a[0]] = {
                'max_rate' : float(a[1]),
                'min_rate' : float(a[2]),
                'decay' : float(a[3]),
                'dry_time' : float(a[4]),
                'max_infil' : float(a[5])
            }

    def make_inflows_dict(self):
        self.inflows = {}
        for l in self._sections['[INFLOWS]']:
            a = l.split()

            self.inflows[a[0]] = {
                'constituent' : a[1],
                'time_series' : a[2],
                'type' : a[3],
                'm_factor' : float(a[4]),
                's_factor' : float(a[5])
            }

            try:
                a[0]['baseline'] = a[6]
                a[0]['pattern'] = a[7]
            except:
                pass
            
    def make_junction_dictionary(self):
        self.junctions = {}

        for l in self._sections['[JUNCTIONS]']:
            a = l.split()

            self.junctions[a[0]] = {
                'elevation': float(a[1]),
                'max_depth': float(a[2]),
                'init_depth': float(a[3]),
                'sur_depth': float(a[4]),
                'a_ponded': float(a[5])
            }

    def make_losses_dict(self):
        self.losses = {}
        for l in self._sections['[LOSSES]']:
            a = l.split()

            self.losses[a[0]] = {
                'k_entry' : float(a[1]),
                'k_exit' : float(a[2]),
                'k_avg' : float(a[3]),
                'flap_gate' : a[4],
                'seepage' : float(a[5])
            }

    def make_map_dict(self):
        dims = self._sections['[MAP]'][0].split() 
        # I think the dimensions are in the order of East, South, West, North
        self.Map = {
            'dim': {
                'east' : dims[1],
                'south' : dims[2],
                'west' : dims[3],
                'north' : dims[4]
            },

            'units' : self._sections['[MAP]'][1].split()[1]
        }

    def make_outfall_dictionary(self):
        self.outfalls = {}

        for l in self._sections['[OUTFALLS]']:
            a = l.split()
            self.outfalls[a[0]] = {
                'elevation': float(a[1]),
                'type': a[2],
            }

            if a[2] == 'FREE':
                self.outfalls[a[0]]['stage_data'] = 0.0
                self.outfalls[a[0]]['gated'] = a[3]
            else:
                self.outfalls[a[0]]['stage_data'] = float(a[3]),
                self.outfalls[a[0]]['gated'] = a[4]

    def make_orifice_dictionary(self):
        self.orifices = {}

        for l in self._sections['[ORIFICES]']:
            a = l.split()
            self.orifices[a[0]] = {
                'from_node': str(a[1]),
                'to_node': str(a[2]),
                'type':a[3],
                'offset':float(a[4]),
                'Cd':float(a[5]),
                'gated':a[6],
                'close_time':float(a[7])
            }

        for l in self._sections['[XSECTIONS]']:
            a = l.split()

            try:
                self.orifices[a[0]]['shape'] = a[1]
                self.orifices[a[0]]['geom1'] = float(a[2])
                self.orifices[a[0]]['geom2'] = float(a[3])
                self.orifices[a[0]]['geom3'] = float(a[4])
                self.orifices[a[0]]['geom4'] = float(a[5])
                self.orifices[a[0]]['barrels'] = int(a[6])
                self.orifices[a[0]]['culvert'] = float(a[7])
            except:
                pass

    def make_options_dictionary(self):
        self.options = {}

        for l in self._sections['[OPTIONS]']:
            a = l.split()
            self.options[a[0]]=a[1]

        step_str = self.options['ROUTING_STEP'].split(':')
        timestep_sec = float(step_str[0])*60*60 + float(step_str[1])*60 + float(step_str[2])
        self.options['ROUTING_STEP'] = timestep_sec

    def make_polygons_dict(self):
        self.polygons = {}

        for p in self._sections['[Polygons]']:
            l = p.split()
            try:
                self.polygons[l[0]]['x'].append(float(l[1]))
                self.polygons[l[0]]['y'].append(float(l[2]))
            except:
                self.polygons[l[0]] = {
                    'x' : [float(l[1])],
                    'y' : [float(l[2])]
                }

    def make_pump_dictionary(self):
        self.pumps = {}
        for l in self._sections['[PUMPS]']:
            a = l.split()
            self.pumps[a[0]] = {
                'from_node':a[1],
                'to_node':a[2],
                'pump_curve':a[3],
                'status':a[4],
                'startup':a[5],
                'shutoff':a[6]
            }

        for p in self.pumps:
            self.pumps[p]['curve_info'] = self.curves[self.pumps[p]['pump_curve']]

    def make_raingauges_dict(self):
        self.raingauges = {}
        for l in self._sections['[RAINGAGES]']:
            a = l.split()
            self.raingauges[a[0]] = {
                'format' : a[1],
                'interval' : float(a[2]),
                'SCF' : float(a[3]),
                'source1' : a[4],
                'source2' : a[5]
            }

    def make_sections(self):
        with open(self.inpF) as f:
            contents = f.read()
        
        self._sections = {}
        for header in self.headers:
            self._sections[header] = contents.find(header)
            
        sort = sorted(self._sections.items(), key=lambda x: x[1])
        
        for i in range(0,len(sort)):
            if i < len(sort)-1:
                a = [sort[i][1],sort[i+1][1]]
            else:
                a = [sort[i][1],len(contents)]
                
            section_content = contents[a[0]:a[1]]
            h = section_content.split('\n')[0]

            self._sections[h] = []
            
            for l in section_content.split('\n'):
                if not l:
                    pass
                elif l[0].isalnum():
                    self._sections[h].append(l)
                else:
                    pass
            
    def make_storage_dictionary(self):
        self.storages = {}

        for l in self._sections['[STORAGE]']:
            a = l.split()

            self.storages[a[0]] = {
                'elevation':float(a[1]),
                'max_depth':float(a[2]),
                'init_depth:':float(a[3]),
                'shape':a[4],
                #Curve Name/Params
                #N/A
                #Fevap
                #PSI
                #Ksat
                #IMD
            }

            if a[4] == 'FUNCTIONAL':
                self.storages[a[0]]['A'] = float(a[5])
                self.storages[a[0]]['B'] = float(a[6])
                self.storages[a[0]]['C'] = float(a[7])

            elif a[4] == 'TABULAR':
                self.storages[a[0]]['curve_name'] = a[5]
                self.storages[a[0]]['curve_info'] = self.curves[a[5]]
                self.storages[a[0]]['curve_info']['x_val'] = [float(i) for i in self.storages[a[0]]['curve_info']['x_val']]
                self.storages[a[0]]['curve_info']['y_val'] = [float(i) for i in self.storages[a[0]]['curve_info']['y_val']]
                self.storages[a[0]]['curve_info']['vol'] = []

            else:
                print(a[0] + ' does not have depth v area info.')

        self.calc_storage_vol()
        
    def make_subcatchment_dictionary(self):
        self.subcatchments = {}

        for l in self._sections['[SUBCATCHMENTS]']:
            a = l.split()

            self.subcatchments[a[0]] = {
                'rain_gage': a[1],
                'outlet': a[2],
                'area': float(a[3]),
                'per_imperv': float(a[4]),
                'width': float(a[5]),
                'slope': float(a[6]),
                'curblen': float(a[7])
            }
            
    def make_timeseries_dict(self):
        self.timeseries = {}
        for l in self._sections['[TIMESERIES]']:
            a = l.split()

            try:
                self.timeseries[a[0]]['time'].append(a[1])
                self.timeseries[a[0]]['value'].append(a[2])
            except:
                self.timeseries[a[0]] = {
                    'time' : [a[1]],
                    'value' : [a[2]]
                }

    def make_xsec_dict(self):
        self.xsections = {}
        for l in self._sections['[XSECTIONS]']:
            a = l.split()

            if len(a) != 8 and len(a) != 6:
                self.warnings.append(a[0] + ' ' + str(len(a)))

            self.xsections[a[0]] = {
                'shape':a[1],
                'geom1' : float(a[2]),
                'geom2' : float(a[3]),
                'geom3' : float(a[4]),
                'geom4' : float(a[5]),
            }

            try:
                self.xsections[a[0]]['barrels'] = int(a[6])
                self.xsections[a[0]]['culvert'] = float(a[7])
            except:
                self.xsections[a[0]]['barrels'] = 1
                self.xsections[a[0]]['culvert'] = 0

        self.calc_xsec_area()

    def make_verts_dict(self):
        self.verts = {}

        for v in self._sections['[VERTICES]']:
            l = v.split()
            try:
                self.verts[l[0]]['x'].append(float(l[1]))
                self.verts[l[0]]['y'].append(float(l[2]))
            except:
                self.verts[l[0]] = {
                    'x' : [float(l[1])],
                    'y' : [float(l[2])]
                }




    # CALC
    def calc_xsec_area(self):
        for item in self.xsections:
            if self.xsections[item]['shape'] == 'CIRCULAR':
                self.xsections[item]['area'] = ( self.xsections[item]['geom1'] / 2 ) ** 2 * math.pi * self.xsections[item]['barrels']
            elif self.xsections[item]['shape'] == 'RECT_CLOSED' or self.xsections[item]['shape'] == 'RECT_OPEN':
                self.xsections[item]['area'] = self.xsections[item]['geom1'] * self.xsections[item]['geom2'] * self.xsections[item]['barrels']
            elif self.xsections[item]['shape'] == 'TRIANGULAR':
                self.xsections[item]['area'] = 0.5 * self.xsections[item]['geom1'] * self.xsections[item]['geom2'] * self.xsections[item]['barrels']
            else:
                self.warnings.append(item + ' ' + self.xsections[item]['shape'] + ' not yet calculated area')
                self.xsections[item]['area'] = 1.0

    def convert(self, conversion):
        to_convert = [self.coords,self.verts,self.polygons]
        for i in to_convert:
            for k in i:
                x = np.array(i[k]['x']) / conversion
                y = np.array(i[k]['y']) / conversion

                i[k]['x'] = x.tolist()
                i[k]['y'] = y.tolist()

    def calc_datum_conversion(self,key_name):
        # apply offset to variables that have elevation:
        #     - Junctions
        #     - Storages
        #     - Outfalls
        for point in self.junctions:
            self.junctions[point][key_name] = self.junctions[point]['elevation'] - self.offset
        for point in self.storages:
            self.storages[point][key_name] = self.storages[point]['elevation'] - self.offset
        for point in self.outfalls:
            self.outfalls[point][key_name] = self.outfalls[point]['elevation'] - self.offset            
            
    def calc_slope(self):
        for item in self.conduits:
            if self.conduits[item]['from_node'] in self.junctions.keys():
                e1 = self.junctions[self.conduits[item]['from_node']]['elevation']+self.conduits[item]['in_offset']
            elif self.conduits[item]['from_node'] in self.storages.keys():
                e1 = self.storages[self.conduits[item]['from_node']]['elevation']+self.conduits[item]['in_offset']
            else:
                e1 = 1

            if self.conduits[item]['to_node'] in self.junctions.keys():
                e2 = self.junctions[self.conduits[item]['to_node']]['elevation']+self.conduits[item]['out_offset']
            elif self.conduits[item]['to_node'] in self.storages.keys():
                e2 = self.storages[self.conduits[item]['to_node']]['elevation']+self.conduits[item]['out_offset']
            else:
                e2 = 1

            if e1==1 or e2==1:
                self.conduits[item]['slope_flag'] = True
            else:
                self.conduits[item]['slope_flag'] = False

            slope = (e1 - e2)/self.conduits[item]['length']

            if slope < self._min_slope:
                slope = self._min_slope
                self.conduits[item]['slope_flag'] = True

            self.conduits[item]['slope'] = slope
            
    def calc_qfull(self):
        for item in self.conduits:
            if self.conduits[item]['shape'] == 'CIRCULAR':
                # compute Qfull as pipe full manning equation
                self.conduits[item]['q_full'] = (self.conduits[item]['geom1']**(8/3)*self.conduits[item]['slope']**(1/2))/(4**(5/3)*self.conduits[item]['roughness'])*math.pi
            elif self.conduits[item]['shape'] == 'RECT_CLOSED':
                # Compute q_full as manning equation of pipe with manning eq with depth as 0.95
                self.conduits[item]['q_full'] = (1.49/self.conduits[item]['roughness']) * (0.95 * self.conduits[item]['geom1'] * self.conduits[item]['geom2']) * (self.conduits[item]['geom2'] * 0.95 * self.conduits[item]['geom1'] / (self.conduits[item]['geom2'] + 2 * 0.95 * self.conduits[item]['geom1']))**(2/3)
            else:
                self.conduits[item]['q_full'] = 1;

    def calc_conduit_vol(self):
        for element in self.conduits:
            self.conduits[element]['vol'] = self.conduits[element]['area'] * self.conduits[element]['length']

    def calc_storage_vol(self):
        for element in self.storages:
            if self.storages[element]['shape'] == 'FUNCTIONAL':
                self.storages[element]['total_storage'] = ( self.storages[element]['A'] * self.storages[element]['max_depth']**(self.storages[element]['B'] + 1) / ( self.storages[element]['B'] + 1 ) ) + ( self.storages[element]['C'] * self.storages[element]['max_depth'] )
            elif self.storages[element]['shape'] == 'TABULAR':
                '''
                'a' is any generic area under a curve.
                FROM SWMM SOURCE CODE:
                    The area within each interval i of the table is given by:
                    Integral{ y(x)*dx } from x(i) to x
                    where y(x) = y(i) + s*dx
                    dx = x - x(i)
                    s = [y(i+1) - y(i)] / [x(i+1) - x(i)]
                    This results in the following expression for a(i):
                    a(i) = y(i)*dx + s*dx*dx/2
                '''
                x = self.storages[element]['curve_info']['x_val']
                y = self.storages[element]['curve_info']['y_val']
                v = [0.0]
                for i in range(1,len(x)):
                    h = x[i] - x[i-1]
                    a = (y[i-1] + y[i])*h/2

                    v.append(v[-1]+a)

                self.storages[element]['curve_info']['vol'] = v

                '''Generally speaking, if the storage curve is tabular then the last value seems to be a really large number that would more closely align with flooding of a "storage" element that is really maybe just a manhole. So, we'll call the total storage approximately being equal to the second to last volume value.'''
                self.storages[element]['total_storage'] = self.storages[element]['curve_info']['vol'][-2]
            else:
                pass

class system():

    def __init__(self, sim, *args, **kwargs):
        self.units = sim.system_units
        self.flood_count = 0.0
        self.tot_flow = 0.0
        self.offset = 0.0
        self.control = True
        self.kwargs = kwargs
        self.group_lookup = dict()
        self.actions = []
        self.control_step = 0.0

        if self.units == 'US':
            self.g = 32.2 # gravity
        else:
            self.g = 9.81 # gravity

        print(self.kwargs)
        kw = self.kwargs.keys()
        if 'offset' in kw:
            self.offset = self.kwargs['offset']
        if 'control' in kw:
            self.control = self.kwargs['control']
        if 'control_step' in kw:
            self.control_step = self.kwargs['control_step']
            

class ControlPoint:
    def __init__(self,line):
        self.c_name = line[0]
        self.c_type = line[1]
        self.action = float(line[2])
        self.u_name = line[3]
        self.u_type = line[4]
        self.u_param = float(line[5])   # Volume parameter weight
        self.ds_param = float(line[10]) # derivative parameter weight
        self.measure = line[6]
        
        self.location = line[8]
        self.group = int(line[9])
        
        self.flood_el = float(line[7])
        self.flooding = False
        self.flood_count = 0.0

        self.q_goal = 0.0

    def set_vars(self,nodes,links):
        # Give nodes and links, sets attributes
        # control element
        self.c_var = links[self.c_name]
    
        # upstream element
        if self.u_type == 'junction' or self.u_type == 'storage':
            self.u_var = nodes[self.u_name]
        elif self.u_type == 'link':
            self.u_var = links[self.u_name]

    def get_target_setting(self,run,nodes,links):
        # Could play with the idea of making nodes a global variable.
        control_connects = self.c_var.connections
        upstream = nodes[control_connects[0]]
        downstream = nodes[control_connects[1]]

        h1 = upstream.depth + upstream.invert_elevation
        h2 = downstream.depth + downstream.invert_elevation
        
        current_setting = self.c_var.current_setting # current_setting == hcrown

        pump = False   
        if self.c_type == 'pump':
            pump = True

        if not pump:
            current_height = current_setting * self.cmi['geom1'] # current_height == hcrown
            h_midpt = (current_height / 2) + (upstream.invert_elevation + downstream.invert_elevation) / 2
            hcrest = upstream.invert_elevation + self.cmi['offset']
            
            # inlet submergence
            if h1 < current_height:
                f = (h1 - hcrest) / (current_height - hcrest) # weir equation
            else:
                f = 1.0 # submerged.
    
            # which head to use
            if f < 1.0:
                H = h1 - hcrest
            elif h2 < h_midpt:
                H = h1 - h_midpt
            else:
                H = h1 - h2
            
            # USE CALCULATED HEAD AND DESIRED FLOW TO DETERMINE GATE OPENING ACTION
            
            # no head at orifice
            if H < 0.1 or f <= 0.0:
                self.action = 0.0
                # print('Head too small')
            elif h2 > h1:
                self.action = 0.0
                print('Backward flow condition, orifice closed')
            
            # Weir Flow
            elif (f < 1.0 and H > 0.1):
                A_open = self.q_goal / ( self.cmi['Cd'] * np.sqrt(2*run.g*H) * (2.0/3.0) )
                
                if self.cmi['shape'] == 'CIRCULAR':
                    print(self.c_name)
                    print("Circular does not work yet. Action = 0.0")
                    self.action = 0.0
                else:
                    A_ratio = A_open / ( self.cmi['geom1'] * self.cmi['geom2'] )
                    self.action = A_ratio
            
            # True orifice flow
            else:
                # since q = Cd * A_open * sqrt( 2 g H )
                A_open = self.q_goal / ( self.cmi['Cd'] * np.sqrt(2*run.g*H) )
                
                if self.cmi['shape'] == 'CIRCULAR':
                    print(self.c_name)
                    print("Circular does not work yet. Action = 0.0")
                    self.action = 0.0
                else:
                    A_ratio = A_open / ( self.cmi['geom1'] * self.cmi['geom2'] )
                    self.action = A_ratio
                    

        # Pump is true
        else: 
            if self.cmi['curve_info']['type'] == 'PUMP1':
                print(self.c_name, 'Pump type 1...')

            elif self.cmi['curve_info']['type'] == 'PUMP2':
                # q_out is a function of depth in wet well.
                
                # get q_full from depth
                depth = upstream.depth
                
                q_full = 0.0
                
                n = len(self.cmi['curve_info']['x_val'])
                for  l in range(n-1,-1,-1):
                    # first index in the list. Can't find negative index.
                    if l  == 0:
                        if depth < self.cmi['curve_info']['x_val'][l]:
                            q_full = self.cmi['curve_info']['y_val'][l]

                    else:
                        if depth < self.cmi['curve_info']['x_val'][l] and depth > self.cmi['curve_info']['x_val'][l-1]:
                            q_full = self.cmi['curve_info']['y_val'][l]        

            elif self.cmi['curve_info']['type'] == 'PUMP3':
                head = h2 - h1 # pump pushes water from low head (h1) to higher head (h2)
                
                # x: Head
                # y: Flow
                # x = [float(j) for j in self.cmi['curve_info']['x_val']] 
                # y = [float(j) for j in self.cmi['curve_info']['y_val']]
                
                if head > max(self.cmi['curve_info']['x_val']):
                    head = max(self.cmi['curve_info']['x_val'])
                elif head < min(self.cmi['curve_info']['x_val']):
                    head = min(self.cmi['curve_info']['x_val'])

                # calculate q_full at given head.
                q_full = np.interp(
                    head,
                    np.array(self.cmi['curve_info']['x_val']),
                    np.array(self.cmi['curve_info']['y_val']),
                    )

            elif self.cmi['curve_info']['type'] == 'PUMP4':
                print(self.c_name, 'Pump type 4...')
            
            if self.q_goal == 0.0:
                self.action = 0.0
            else:
                self.action = self.q_goal / q_full 
        
        # if target setting greater than 1, only open to 1.
        self.action = min(max(self.action,0.0),1.0)

        self.check_flooding(run,nodes,links)
        # print(self.c_name,self.c_var.target_setting)
        self.c_var.target_setting = self.action

    def check_flooding(self,run,nodes,links):
        self.flooding = False

        if isinstance(self.u_var, pyswmm.nodes.Node):
            # get node elevation
            elev = self.u_var.depth + self.u_var.invert_elevation
        elif isinstance(self.u_var, pyswmm.links.Link):
            # get inlet node's elevation for the link
            elev =  nodes[self.u_var.inlet_node].depth + nodes[self.u_var.inlet_node].invert_elevation
        
        if elev + run.offset > self.flood_el:
            self.flooding = True
            self.action = 1.0
            self.flood_count = self.flood_count + 1.0

    def get_model_info(self,model):
        # print(self.c_name,self.c_type)
        # print(self.u_name,self.u_type)

        if self.c_type == 'pump':
            self.cmi = model.pumps[self.c_name]
            self.cmi['curve_info']['x_val'] = [float(i) for i in self.cmi['curve_info']['x_val']]
            self.cmi['curve_info']['y_val'] = [float(i) for i in self.cmi['curve_info']['y_val']]
        elif self.c_type == 'orifice':
            self.cmi = model.orifices[self.c_name]

        if self.u_type == 'storage':
            self.umi = model.storages[self.u_name]
            self.max_depth = self.umi['max_depth']
            self.max_vol = self.umi['total_storage']
        elif self.u_type == 'link':
            self.umi = model.conduits[self.u_name]
            self.max_depth = self.umi['geom1']
            self.max_vol = self.umi['vol']

    def get_measure(self):
        if self.measure == 'depth':
            self.now = self.u_var.depth
        elif self.measure == 'flow':
            print(self.name, 'tryna get flow...')
        else:
            print(self.name, 'did not grab measure. Inspect')

class DownstreamPoint:
    def __init__(self,line):
        self.d_name = line[0]
        self.d_type = line[1]
        self.measure = line[2]
        self.epsilon = float(line[3])
        self.gamma = float(line[4])
        self.max_depth = float(line[5])
        self.set_point = float(line[6])
        self.set_derivative = float(line[7])
        self.location = line[8]
        self.group = int(line[9])
        self.derivative = 0.0

    def set_vars(self,nodes,links):
        print(self.d_type)
        if self.d_type == 'storage':
            self.d_var = nodes[self.d_name]
        elif self.d_type == 'link':
            self.d_var = links[self.d_name]

    def get_model_info(self,model):
        print('Downstream Points')
        print(self.d_name,self.d_type)

        if self.d_type == 'storage':
            self.dmi = model.storages[self.d_name]
            self.max_vol = self.dmi['total_storage']
        elif self.d_type == 'link':
            self.dmi = model.conduits[self.d_name]
            self.max_vol = self.dmi['vol']

    def get_measure(self):
        if self.measure == 'depth':
            self.now = self.d_var.depth
        elif self.measure == 'flow':
            print('did not write flow yet. Turn around...')
        else:
            print(self.d_name,' did not grab measure. Inspect')


# MAKE
def make_control_points(fn):
    ControlPoints = []
    with open(fn,'r') as f:
        next(f)
        for line in f:
            line = line.strip('\n').split(',')
            ControlPoints.append(ControlPoint(line))
            
    return ControlPoints

def make_downstream_points(fn):
    DownstreamPoints = []
    with open(fn,'r') as f:
        next(f)
        for line in f:
            line = line.strip('\n').split(',')
            DownstreamPoints.append(DownstreamPoint(line))

    return DownstreamPoints




def orifice_xsect_grab(controlDict,orifices):
    # Add items from orifices dictionary to the control dict
    for i in controlDict:
        try:
            controlDict[i].update(orifices[i])
        except:
            pass
        
def pump_curve_grab(controlDict, pumps):
    # Add information to controlDict with pump curve info.
    for i in controlDict:
        try:
            controlDict[i].update(pumps[i])
        except:
            pass

def get_depth(elements,conduitDict,storageDict):
    for element in elements:
        if elements[element]['type'] == 'link':
            elements[element]['max_depth'] = conduitDict[element]['geom1']
        elif elements[element]['type'] == 'storage':
            elements[element]['max_depth'] = storageDict[element]['max_depth']
        else:
            pass

def get_q_full_and_other(elements,conduits,storages,junctions):
    for element in elements:
        if elements[element]['type'] == 'link':
            elements[element]['max_flow'] = conduits[element]['q_full']
        elif elements[element]['type'] == 'storage':
            elements[element]['total_storage'] = storages[element]['total_storage']
        elif elements[element]['type'] == 'junction':
            elements[element]['max_depth'] = junctions[element]['max_depth']
        else:
            pass

# SAVING

def push_meta(run,outF,ControlPoints,DownstreamPoints,derivative):
    # Make string to push to csv metadata file
    push_list = []

    push_list.append(run.flood_count)
    push_list.append(outF)
    for g in range(1,run.groups+1):
        print(g+1)
        push_list.append('Group' + str(g))
        
        push_list.append('UP')
        cps = [c for c in ControlPoints if c.group == g]
        for c in cps:
            push_list.append(c.u_name)
            push_list.append(c.u_param)
            
            if derivative:
                push_list.append(c.ds_param)
        
        push_list.append('DOWN')
        dps = [d for d in DownstreamPoints if d.group == g]
        for d in dps:
            push_list.append(d.d_name)
            push_list.append(d.epsilon)
            push_list.append(d.set_point)
            
            if derivative:
                push_list.append(d.gamma)
                push_list.append(d.set_derivative)

    push_str = ','.join(map(str, push_list))
    return push_str


# PLOTTTING Stuff
def make_extract_string(name,el_type,measure):

    node_keys = {'depth': 'Depth_above_invert',
                'head': 'Hydraulic_head',
                'volume': 'Volume_stored_ponded',
                'inflow_lat': 'Lateral_inflow',
                'flow': 'Total_inflow',
                'flooding': 'Flow_lost_flooding'}
    link_keys = {'flow': 'Flow_rate',
                'depth': 'Flow_depth',
                'velocity': 'Flow_velocity',
                'froude': 'Froude_number',
                'cap': 'Capacity'}
        

    if el_type == 'storage' or el_type == 'junction':
        el_type = 'node'
        measure = node_keys[measure]
    else:
        measure = link_keys[measure]
        #el_type already link
        
    return el_type + ',' + name + ',' + measure

# def performance_elements(elements,conduits,nodes,storages,subcatchments,outfalls,orifices):
#     for element in elements:
#         if elements[element]['type'] == 'outfall':
#             elements[element]['elevation'] = outfalls[element]['elevation']
#             elements[element]['elev_detroit'] = outfalls[element]['elev_detroit']
#         elif elements[element]['type'] == 'link':
#             elements[element]['max_depth'] = conduits[element]['geom1']
#         elif elements[element]['type'] == 'storage':
#             elements[element]['max_depth'] = storages[element]['max_depth']
#         elif elements[element]['type'] == 'orifice':
#             elements[element]['max_depth'] = orifices[element]['geom1']
#         else:
#             pass

# def return_inputs(filename,handle):
#     #
#     df = pd.read_csv(filename,index_col='name')
#     df.index = df.index.map(str)
#     df_dict = df.to_dict(into=OrderedDict,orient='index')

#     for i in df_dict:
#         if handle == 'control':
#             df_dict[i]['actionTS'] = []
#             df_dict[i]['q_goal'] = 1.0
#             df_dict[i]['PD'] = 0.0
#         elif handle == 'upstream':
#             df_dict[i]['ts'] = []
#             df_dict[i]['PD'] = []
#             df_dict[i]['ts_el'] = []
#         elif handle == 'downstream':
#             df_dict[i]['ts_flow'] = []
#             df_dict[i]['ts_depth'] = []
#         elif handle == 'performance':
#             df_dict[i]['ts_flow'] = []
#             df_dict[i]['ts_depth'] = []
#         else:
#             pass

#     return df_dict        


# def make_control(cF,uF):
#     # Normal processing of the control csv into a dictionary
#     CD = return_inputs(cF,'control')
    
#     for c in CD:
#         CD[c]['upst'] = {CD[c]['upst']:{}}
        
#     for c in CD:
#         for i in CD[c]['upst']:
#             a = from_csv(CD[c]['group'],c,uF)
#             CD[c]['upst'] = a
    
#     # run check
#     for c in CD:
#         for u in CD[c]['upst']:
#             if c != CD[c]['upst'][u]['DScp']:
#                 print(c, CD[c]['upst'][u]['DScp'], 'are not the same')
    
#     return CD

# def from_csv(group,i,uF):
#     df = pd.read_csv(uF,index_col='name')
#     a = df.loc[(df['group'] == group) & (df['DScp'] == i)]
#     a.index = a.index.map(str)
#     a_dict = a.to_dict(into=OrderedDict,orient='index')
    
#     for i in a_dict:
#         a_dict[i]['ts'] = []
#         a_dict[i]['PD'] = []
#         a_dict[i]['ts_el'] = []
    
#     return a_dict