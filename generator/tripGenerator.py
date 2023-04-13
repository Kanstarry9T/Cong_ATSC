import networkx as nx
import numpy as np
import pickle
import json
import time
import multiprocessing as mp
import xml.dom.minidom as minidom
import os
import argparse
from haversine import haversine
import math
import csv
from openpyxl import load_workbook
'''
0831 todo:
    - 1. add gravity model
    - 2. add BPR function for route choice
'''

class Generator:

    def __init__(self, roadnet_path, num_trips, city_params, gravity_params, bpr_params, sim_len=3600, unitlon=0.02,unitlat=0.02,numRows=6, numColumns=8, road_cap=1000):
        '''
        :param roadmap_path: road map file
        :param graph: whether to build road graph again
        :param roadgraph_path: path to load road graph
        '''
        # initial run and get roadgraph from roadnet.txt file
        self.roadnet_path = roadnet_path
        self.roadgraph = None # a networkX Graph instance
        self.traffic_duration = sim_len # By default, 3600-second traffic sample data is generated
        self.bpr_params = bpr_params
        self.gravity_params = gravity_params
        self.cap = road_cap
        # self.beta = beta
        self.num_trips = num_trips

        self.unit_lon = unitlon
        self.unit_lat = unitlat
        self.numRows = numRows
        self.numColumns = numColumns
         
        # read roadnet.txt file
        self.area, self.road_len = self.read_roadnet(roadnet_path=roadnet_path) # area of the selected rectangle zone, in km2

        self.pop = city_params['popdensity']*self.area # total population within the zone

        print('there are a total of {} population within the zone of area {}'.format(self.pop, self.area))

        
        self.generate_roadGraph()
        self.edge_id_list = [self.roadgraph[e[0]][e[1]]['id'] for e in self.roadgraph.edges()]

        
        self.zone_info = self.get_trafficZones() # divide the road network into traffic zones
        self.ODdemand, self.Odemand, self.total_trips = self.get_ODdemand()

        print('there are a total of {} trips to be generated!'.format(self.total_trips))
        print('the min and max of trips start from a traffic zone are {}, {}'.format(min(self.Odemand.values()), max(self.Odemand.values())))
    
    # def set_signal(self, func, params, alarm=10):
    #     '''
    #     set signal for too long running time
    #     '''
    #     signal.signal(signal.SIGALRM, self._signal_handler(func, params))
    #     signal.alarm(alarm) 

    
    # def _signal_handler(self, func, params):
    #     print('time out')
    #     func(*params)


    def get_trafficZones(self):
        '''
        Divide road network into numRows * numColumns rectangle traffic zones
        return: IDs (rowIndex, columnIndex) of created traffic sub-zones
        '''

        self.numColumns = math.ceil((self.right_lon - self.left_lon) / self.unit_lon)
        # print(self.right_lon, self.left_lon, self.numColumns, self.unit_lon)
        self.numRows = math.ceil((self.top_lat - self.bottom_lat) / self.unit_lat)
        print(self.numRows)
        print(self.numColumns)
        zone_info = {}
        # print("Row:{}, Col:{}".format(self.numRows, self.numColumns))
        for row in range(self.numRows):
            for col in range(self.numColumns):
                zone_info[(row, col)] = {
                    'inters_id': [], # a list of IDs of intersections
                    'left_lon': self.left_lon + col*self.unit_lon, # leftmost longitude of the zone
                    'right_lon': self.left_lon + (col+1)*self.unit_lon, # rightmost logitude of the zone
                    'top_lat': self.top_lat - row*self.unit_lat, # top latitude of the zone
                    'bottom_lat':self.top_lat - (row+1)*self.unit_lat, # bottom latitude of the zone
                    'num_inters': 0, # number of intersections within the zone
                    'num_signals': 0, # number of signalized intersections within the zone
                    'roadlen': 0.0, # road length within the zone
                    'roadseg':0, # number of road segments within the zone
                }
        cnt = 0
        for key in self.inter_info.keys():
            if key in self.roadgraph.nodes():
                # print('{} in nodes'.format(key))
                cnt += 1
                zone_id = self.get_inter_zoneID(key)
                zone_info[zone_id]['inters_id'].append(key)
                zone_info[zone_id]['num_inters'] += 1
                zone_info[zone_id]['num_signals'] += self.inter_info[key]['sign']
                zone_info[zone_id]['roadlen'] += self.inter_info[key]['roadlen']
                zone_info[zone_id]['roadseg'] += self.inter_info[key]['roadseg']
        print('Divide road network into {}*{} traffic zones successfully!'.format(self.numRows, self.numColumns))
        n_inters = len(self.inter_info)
        print('original inter count {} - new inter count {} = {}'.format(n_inters, cnt, n_inters-cnt))


        # post-process to get zone center point and population data
        total_pop = 0
        for row in range(self.numRows):
            for col in range(self.numColumns):
                zone = zone_info[(row, col)]
                left, right, top, bottom = zone['left_lon'], zone['right_lon'], zone['top_lat'], zone['bottom_lat']
                num_inters, road_len = zone['num_inters'], zone['roadlen']
                zone['center'] = ((top+bottom)/2, (left+right)/2) # (lat, lon)
                zone['diameter'] = 2 * haversine(zone['center'], (top, left))
                zone_pop = self._get_pop(road_len, num_inters) 
                zone['pop'] = zone_pop
                total_pop += zone_pop
        
        # # Estimate the OD demand (in form of probabilities) based on road network information
        # self.get_Oprob(Oprob_mode) # Get probabilities of a vehicle departs from zones (Origin zone) of the road network
        # self.get_ODprob(prob_corner, prob_mid) #Get probabilities of a vehicle depart from an Origin zone and arrived into a Destination zone
        print('the zone info is 0,0 road {}, pop {}'.format(int(zone_info[(0,0)]['roadlen']), zone_info[(0,0)]['pop']))
        print('the zone info is 0,1 road {}, pop {}'.format(int(zone_info[(0,1)]['roadlen']), zone_info[(0,1)]['pop']))
        print('total road length is {}'.format(self.road_len))
        print('total pop after processing is {}'.format(total_pop))
        return zone_info 
    
    def _get_pop(self, road_len, num_inters):
        '''
        helper function to get population within a traffic zone
        beta: the scaling parameter of road length over population
        r = p0 * p^beta, (r'/r) = (p'/p)^beta, p' = p * (r'/r) ^ (1/beta)
        '''
        if num_inters <= 0:
            return 0
        
        return int(self.pop * (road_len/self.road_len)) # ** (1/self.beta)

    def get_ODdemand(self):
        '''
        get trip demands between pairwise origin_zone and dest_zone
        '''
        # get parameters for gravity model
        a, b, c, d = self.gravity_params['a'], self.gravity_params['b'], self.gravity_params['c'], self.gravity_params['d']

        ODdemand = dict()
        total_demand = 0
        Odemand = {k: 0 for k in self.zone_info.keys()}
        
        for k0, v0 in self.zone_info.items():
            for k1, v1 in self.zone_info.items():
                if k0 == k1:
                    dist = v0['diameter']  
                else:
                    dist = haversine(v0['center'], v1['center'])  
                pop0, pop1 = v0['pop'], v1['pop']
                demand = max(10, int((pop0 ** a * pop1 ** b) / (d * dist ** c)))
                ODdemand[(k0, k1)] = demand
                total_demand += demand
                Odemand[k0] += demand
        
        ODdemand1 = {k: self.num_trips * v/total_demand for k, v in ODdemand.items()}
        Odemand1 = {k: self.num_trips * v/total_demand for k, v in Odemand.items()}
        # print(Odemand[(0,0)])
        return ODdemand1, Odemand1, total_demand
    
    def generate_trips(self):
        '''
        Generate initial traffic flow data given the road network data 
        :param numVeh: total number of vehicles that will enter the network in 1-hour
        :param percentVeh: percentages of vehicles that will enter the network in each period (e.g., in 4-minute)  
        :param weight: the larger the weight, the more diverse of route choice given Origin-Destination of a trip 
        '''
        print("Start to generate traffic flows!")
            # by default, use length + beta * num_expected_passed_vehicle as edge weight to find shortest_path
            # if mode != None, other options for edge weight

        if self.zone_info is None:
            exit('You need to divide road network into traffic sub-zones!')

        # params = list()
        # res_list = list()
        self.flow = dict()
        self.trips = list()
        self.gen_trips = 0

        # step 1 create params

        for k, num_trips in self.ODdemand.items():
            OzoneID, DzoneID = k
            Ozone = self.zone_info[OzoneID]
            Dzone = self.zone_info[DzoneID]

            Onum_inters = Ozone['num_inters']
            Dnum_inters = Dzone['num_inters']
            
            if Onum_inters == 0 or Dnum_inters == 0:
                # print('Due to no origin/dest intersections, there will be no trips from {} to {}'.format(OzoneID, DzoneID))
                self.total_trips -= num_trips
                continue

            if num_trips <= 0:
                print('There is no trips from {} to {}'.format(OzoneID, DzoneID))
                continue

            trips = self.Odemand[OzoneID]
            trips_perInter = trips / Onum_inters

            # if OzoneID == (0,0):
            #     print('trips per inter is {}'.format(trips_perInter))
            
            o_set = set(Ozone['inters_id'])
            Dinters = Dzone['inters_id']

            n_ointers = max(1, int(num_trips / trips_perInter))
            # if n_ointers == 1:
            #     print('Average number trips per inter between {}, {} is {}, but with {} gen_trips'.format(OzoneID, DzoneID, trips_perInter, num_trips))

            gen_trips = num_trips / n_ointers    
            Ointers = np.random.choice(list(o_set), n_ointers)
            o_set -= set(Ointers)
            flag_for_case = False
            for o_interid in Ointers:
                d_interid = np.random.choice(Dinters)
                while d_interid == o_interid:  # make sure that origin and destination nodes are different
                    if len(Dinters) == 1:
                        flag_for_case = True
                        break
                    else:

                        d_interid = np.random.choice(Dinters)
                if flag_for_case:
                    break
                    
                start_time = 1
                end_time = self.traffic_duration
                flow_data, trip_info = self._generate_trip(o_interid, d_interid, gen_trips, start_time, end_time)
                #print(trip_info)

                if flow_data:
                    self.flow.update(flow_data)
                    self.trips.append(trip_info)
                    #print(self.trips)
                else:
                    print('there is no trip between {} and {}, need to retry generation'.format(o_interid, d_interid))
                    params = (o_interid, d_interid, gen_trips, start_time, end_time, Dinters)
                    self._retry_generation(params)            
        
        print('After generation, the generated trips are {}'.format(self.gen_trips))


    def _retry_generation(self, params, max_retry=5):
        retry = 0
        o_interid, d_interid, gen_trips, start_time, end_time, Dinters = params
        while retry <= max_retry:
            d_interid = np.random.choice(Dinters)
            flow_data, trip_info = self._generate_trip(o_interid, d_interid, gen_trips, start_time, end_time)
            
            if flow_data:
                self.flow.update(flow_data)
                self.trips.append(trip_info)
                print('Success retry for {} == {}'.format(o_interid, retry))
                break
            retry += 1

                        
    def _generate_trip(self, O_interid, D_interid, numVeh, start_time, end_time):
        '''
        :1) generate flow of trips data
        :2) get edge flow pair information
        '''
        # print('start generate trip from {} to {}'.format(O_interid, D_interid))
        start_time = int(start_time)
        end_time = int(end_time)

        flow_id = str(O_interid) + '_' + str(D_interid) + '_' + str(start_time)
        flow_data = dict()
        # edge_flow = dict()

        # step 1: run shortest_path, default - Dijkstra 

        try:
            path_nodes = nx.shortest_path(self.roadgraph, source=O_interid, target=D_interid, weight='weight') # return a list of intersection IDs
        except:
            print("no path nodes")
            return None, None

        # step 2: post-processing

        if len(path_nodes) <= 3: # we omit the vehicle trips with number of edges <= 2
            # print("path nodes less than 3")
            return None, None

        interval = max(1,int((end_time - start_time) / numVeh))
        tmp_data = []

        # append flow information for re-generate traffic
        tmp_data.append(O_interid)
        tmp_data.append(D_interid)
        tmp_data.append(numVeh)
        self.gen_trips += numVeh

        # append shared information
        tmp_data.append(start_time)
        tmp_data.append(end_time)

        # todo1

        # append information to write flow data
        tmp_data.append(interval)
        tmp_data.append(len(path_nodes) - 1) # append number of edges (road segments)

        trip_length = 0

        for idx in range(len(path_nodes) - 1):
            source = path_nodes[idx]
            target = path_nodes[idx + 1]

            link = self.roadgraph[source][target]
            link_id = link['id']
            link['numveh'] += numVeh

            # apply BPR function to update weight of road links
            link['weight'] += link['fftt'] * (1 + self.bpr_params['a'] * (link['numveh'] / self.cap) ** self.bpr_params['b'])
            trip_length += link['length']

            tmp_data.append(link_id)
        
        flow_data[flow_id] = tmp_data
        # trip_info = (numveh, trip_length)
        trip_info = (trip_length, numVeh)
        
        return flow_data, trip_info

        
    def output_cbengine(self, output_path):
        '''
        Write the traffic flow data into a .txt file
        :param output_path:
        :return: self.zone_info.keys()
        '''
        file = open(output_path['flow'], 'w')
        file.write("{}\n".format(len(self.flow)))
        for flow_data in self.flow.values():
            i = flow_data[3:]

            for j in range(len(i)):
                if (j == 2) or (j == 3) or (j == len(i) - 1):
                    file.write("{}\n".format(i[j]))
                else:
                    file.write("{} ".format(i[j]))
        file.close()
        totnum=0
        lennum=0
        delnum=0
        for i in self.trips:
            totnum+=i[1]
            lennum+=i[0]*i[1]
        mean = lennum / totnum
        for i in self.trips:
            delnum+=(i[0]-mean)**2*i[1]
        var = delnum / totnum



        infoData = {'total_trips': self.gen_trips, 'trip_mean': mean, 'trip_var':var}
        with open(output_path['info'], 'w') as f:
            json.dump(infoData, f)
        return self.gen_trips,mean,var
        
    def output_cityflow(self, output_path):
        '''
        Write the traffic flow data into a .txt file
        :param output_path:
        :return: self.zone_info.keys()
        '''
        flow_list = []
        for flow_data in self.flow.values():
            vehicle = {
                "vehicle": {
                "length": 5.0,
                "width": 2.0,
                "maxPosAcc": 2.0,
                "maxNegAcc": 4.5,
                "usualPosAcc": 2.0,
                "usualNegAcc": 4.5,
                "minGap": 2.5,
                "maxSpeed": 16.67,
                "headwayTime": 1.5
                },
                "route": [str(i) for i in flow_data[7:]],
                "interval": flow_data[5],
                "startTime": flow_data[3],
                "endTime": flow_data[4]
            }
            flow_list.append(vehicle)
        with open(output_path, 'w') as file:
            json.dump(flow_list, file)
        
    def output_sumo(self, output_path):
        '''
        Write the traffic flow data into a .txt file
        :param output_path:
        :return: self.zone_info.keys()
        '''
        dom = minidom.getDOMImplementation().createDocument(None,'routes',None)
        root = dom.documentElement
        vType = dom.createElement('vType')
        vType.setAttribute('id', 'Car')
        vType.setAttribute('accel', "2.6")
        vType.setAttribute('decel', "4.5")
        vType.setAttribute('sigma', "0.5")
        vType.setAttribute('length', "5")
        vType.setAttribute('maxSpeed', "16.67")
        root.appendChild(vType)

        flow_list = []
        for id, flow_data in self.flow.items():
            pass
        sorted_flow = sorted(self.flow.items(), key=lambda flow: flow[1][3])
        for (id, flow_data) in sorted_flow:
            str_route = ""
            for road in flow_data[7:]:
                if road != flow_data[7]:
                    str_route = str_route + " " + str(road)
                else:
                    str_route = str(road)
            flow = dom.createElement('flow')
            flow.setAttribute('id', str(id))
            flow.setAttribute('type', "Car")
            flow.setAttribute('begin', str(flow_data[3]))
            flow.setAttribute('end', str(flow_data[4]))
            flow.setAttribute('period', str(flow_data[5]))
            route = dom.createElement('route')
            route.setAttribute('edges', str_route)
            flow.appendChild(route)
            root.appendChild(flow)
        with open(output_path, 'w', encoding='utf-8') as f:
            dom.writexml(f, addindent='\t', newl='\n',encoding='utf-8')
        '''
        <flow id="type1" color="1,1,0"  begin="0" end= "7200" period="900" type="BUS">
            <route edges="beg middle end rend"/>
        </flow>
        
        <flow id="01" type="Car" begin="0" end="72000" number="2400" 
            from="edge1-0" to="edge0-2" departPos="1" departLane="best" departSpeed="5.0"/>
        '''

    def get_zoneInfo(self, zoneid=None):
        '''Return information of a traffic zone given zoneID'''
        if zoneid is None:
            return self.zone_info
        if zoneid[0] not in range(self.numRows) or zoneid[1] not in range(self.numColumns):
            print('Error: zone id')
            return
        print(self.zone_info[zoneid])
        return self.zone_info[zoneid]

    def get_inter_zoneID(self, inter_id):
        '''Given an intersection ID, return the traffic zone ID - (rowIndex, columnIndex)'''
        lat = self.inter_info[inter_id]['lat']
        lon = self.inter_info[inter_id]['lon']
        row = int((lat - self.bottom_lat) / self.unit_lat)
        col = int((lon - self.left_lon) / self.unit_lon)
        return (row, col)

    def generate_roadGraph(self):
        '''Translate roadnetwork data into networkX format, return a networkX graph'''
        DG = nx.DiGraph()
        for key in self.inter_info.keys():
            DG.add_node(key, **self.inter_info[key])  # node_id
        for key in self.road_info.keys():
            pair = (self.road_info[key]['ininter_id'], self.road_info[key]['outinter_id'])
            road_length = self.road_info[key]['roadlen']
            speed = self.road_info[key]['speed']
            fftt = road_length / speed
            DG.add_edge(*pair, **{"id": key, "length": road_length, "speed": speed, 'numveh': 0, 'fftt': fftt, 'weight': fftt})

        # gpickle_file = self.roadnet_path.replace('.txt', '.gpickle')
        # nx.write_gpickle(DG, gpickle_file)
        print('Building road networkX graph successfully!')
        SG = [DG.subgraph(c).copy() for c in sorted(nx.weakly_connected_components(DG), key=len, reverse=True)]
        print('there are {} subgraphs, with lengths of {}'.format(len(SG), [len(c) for c in SG]))
        self.roadgraph = SG[0]
        print('the number of nodes of roadgraph is {}'.format(len(self.roadgraph)))

    def read_pkl(self, roadnet_path):
        f = open(roadnet_path,'rb')
        roadnet_dict = pickle.load(f)
        
        min_lat, max_lat = 1000, -1000
        min_lon, max_lon = 1000, -1000
        
        self.inter_num = len(roadnet_dict['inter'])
        self.inter_info = {}
        print("Total number of intersections:{}".format(self.inter_num))
        for k, v in roadnet_dict['inter'].items():
            self.inter_info[k] = {'lat': v['lat'], 'lon': v['lon'], 
                                  'sign': v['sign'], 'roadlen': 0.0, 
                                  'roadseg':len(v['start_roads'])+len(v['end_roads'])}
            if v['lat'] < min_lat:
                min_lat = v['lat']
            if v['lat'] > max_lat:
                max_lat = v['lat']
            if v['lon'] < min_lon:
                min_lon = v['lon']
            if v['lon'] > max_lon:
                max_lon = v['lon']
            
        self.road_num = len(roadnet_dict['inter'])
        self.road_info = {}
        print("Total number of road segments:{}".format(self.road_num))
        for k, v in roadnet_dict['road'].items():
            self.road_info[k] = {'ininter_id': v['start_inter'], 'outinter_id': v['end_inter'],
                                        'roadlen': v['roadlen'], 'speed': 16.67}
            self.inter_info[v['start_inter']]['roadlen'] += v['roadlen']
            self.inter_info[v['end_inter']]['roadlen'] += v['roadlen']
            
        # update bbox    
        self.left_lon = min_lon - 1e-6
        self.right_lon = max_lon + 1e-6
        self.bottom_lat = min_lat - 1e-6
        self.top_lat = max_lat + 1e-6
        print(self.left_lon, self.right_lon, self.bottom_lat, self.top_lat)


    def read_roadnet(self, roadnet_path):
        '''Read road network data'''
        roadnet = open(roadnet_path, 'r')

        self.min_lat, self.max_lat = 1000, -1000
        self.min_lon, self.max_lon = 1000, -1000

        # read inters
        self.inter_num = int(roadnet.readline())
        self.inter_info = {}
        print("Total number of intersections:{}".format(self.inter_num))
        for _ in range(self.inter_num):
            line = roadnet.readline()
            lat, lon, inter_id, sign = self.read_inter_line(line)
            self.inter_info[inter_id] = {'lat': lat, 'lon': lon, 'sign': sign, 'roadlen': 0.0, 'roadseg':0}

        # read roads
        self.road_info = {}
        self.road_num = int(roadnet.readline())
        road_len = 0
        print("Total number of road segments:{}".format(self.road_num))
        for _ in range(self.road_num):
            line = roadnet.readline()
            inter_id1, inter_id2, roadlen, speed, road_id1, road_id2 = self.read_road_line(line)
            road_len += roadlen * 2
            #print(road_id1, road_id2)
            self.road_info[road_id1] = {'ininter_id': inter_id1, 'outinter_id': inter_id2,
                                        'roadlen': roadlen, 'speed': speed}
            self.road_info[road_id2] = {'ininter_id': inter_id2, 'outinter_id': inter_id1,
                                        'roadlen': roadlen, 'speed': speed}
            self.inter_info[inter_id1]['roadlen'] += roadlen
            self.inter_info[inter_id2]['roadlen'] += roadlen
            self.inter_info[inter_id1]['roadseg'] += 1
            self.inter_info[inter_id2]['roadseg'] += 1
            roadnet.readline()
            roadnet.readline()
        roadnet.close()

        self.left_lon = self.min_lon - 1e-6
        self.right_lon = self.max_lon + 1e-6
        self.bottom_lat = self.min_lat - 1e-6
        self.top_lat = self.max_lat + 1e-6

        long = haversine((self.bottom_lat, self.left_lon), (self.bottom_lat, self.right_lon))
        wide = haversine((self.bottom_lat, self.left_lon), (self.top_lat, self.left_lon))
        print('the left, right, top, down are {}, {}, {}, {}'.format(self.left_lon, self.right_lon, self.bottom_lat, self.top_lat))
        return long * wide, road_len # area in km2
        
    def read_inter_line(self, line):
        '''Read intersection data line-by-line'''
        line = line.split()
        lat = float(line[0])
        lon = float(line[1])

        # update min, max of lat, lon

        if lat < self.min_lat:
            self.min_lat = lat
        if lat > self.max_lat:
            self.max_lat = lat
        if lon < self.min_lon:
            self.min_lon = lon
        if lon > self.max_lon:
            self.max_lon = lon

        inter_id = int(line[2])
        signal = bool(line[3])
        return lat, lon, inter_id, signal

    def read_road_line(self, line):
        '''Read road segment data line-by-line'''
        line = line.split()
        inter_id1 = int(line[0])
        inter_id2 = int(line[1])
        roadlen = float(line[2])
        speed = float(line[3])

        road_id1 = int(line[6])
        road_id2 = int(line[7])
        return inter_id1, inter_id2, roadlen, speed, road_id1, road_id2

def getinter(roadnet_path):
    '''Read road network data'''
    roadnet = open(roadnet_path, 'r')
    return int(roadnet.readline())


def main(city, num_trips, popdensity):
    roadnet_path = os.path.join(city, 'roadnet.txt')
    output_path = {'flow': os.path.join(city, 'flow.txt'), 'info': os.path.join(city, 'info.json')} # trip information, area, ODdemand, etc..

    city_params = {'popdensity':popdensity} # population density of city
    g_params = {'a': .3, 'b': .64, 'c': 3.05, 'd': 8} # params for gravity model
    b_params = {'a': .15, 'b': 4} # parameters for bpr function
    inter_num=getinter(roadnet_path)
    t0 = time.time()
    gen = Generator(roadnet_path, num_trips,city_params, g_params, b_params)
    gen.generate_trips()
    t1 = time.time()
    print('the trip generation time is {}'.format(t1 - t0))

    trnum,mean,var=gen.output_cbengine(output_path)
    return inter_num,trnum,mean ,var


if __name__ == "__main__":
    print('run trip generator')
    parser = argparse.ArgumentParser(
        prog="trip_generator",
        description="1"
    )
    '''
       Read city parameter from Excel file
       Read city Road data from roadnet.txt file
       for any city, some datas/parameters are needed:
          1.the total amount of trip wanted to generate
          2.the area, the population (or the population density of city)
          3.the road data of city(in roadnet.txt)
       then the Gravity Method will help you gen the flow
    '''
    np.random.seed(137)
    args = parser.parse_args()
    wb = load_workbook('citylist.xlsx')
    sheet = wb['0924Road_network']
    Upper_rate=0.0 #you can make it bigger the simulate bigger flow
    for i in range(100):
        city_name=sheet['A{}'.format(i + 2)].value
        trip_num=float(sheet['L{}'.format(i + 2)].value)*(1+Upper_rate)
        popdensity=float(sheet['H{}'.format(i + 2)].value)
        # if you use the area and the population instead,then let popdensity = population/area
        inter_num,trnum,mean,var=main(city_name,trip_num,popdensity)
        sheet['M{}'.format(i + 2)]=trnum
        sheet['N{}'.format(i + 2)] = mean
        sheet['O{}'.format(i + 2)] = var
        sheet['Q{}'.format(i + 2)] = inter_num

    '''the data of flow generated will store here'''
    wb.save('flow_data.xlsx')
