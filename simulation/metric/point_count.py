import numpy as np


class pointoutMetric():
    def __init__(self, world):
        self.world = world
        self.world.subscribe(["vehicles", "time"])
        self.vehicle_enter_time = {}
        self.travel_dis = 0
        self.num = 0
        self.point_cnt={}
        self.road_cnt={}
        self.carwhere={}
        self.travel_time = {}

    def reset(self):
        self.vehicle_enter_time = {}
        self.travel_dis = 0
        self.num = 0
        self.point_cnt = {}
        self.road_cnt = {}
        self.carwhere = {}
        self.travel_time = {}

    def restart(self):
        self.road_cnt={}

    def total_query(self):

        cnt_set = {}

        for p in self.world.intersections:
            cnt = 0
            try:
                roads = self.world.agents[p.id][4:]

                for i in range(4):
                    if roads[i] in self.road_cnt.keys():
                        cnt += self.road_cnt[roads[i]]
            except:
                pass

            cnt_set[p.id]=cnt


        return cnt_set

    def query(self,id):

        cnt = 0

        roads = self.world.agents[id][4:]

        for i in range(4):
            if roads[i] in self.road_cnt.keys():
                cnt += self.road_cnt[roads[i]]


        return cnt

    def update(self, done=False):

        vehicles = self.world.get_info("vehicles")
        current_time = self.world.get_info("time")

        for vehicle in vehicles:

            veh_info = self.world.eng.get_vehicle_info(vehicle)

            if not vehicle in self.vehicle_enter_time:

                self.vehicle_enter_time[vehicle] = current_time
                self.carwhere[vehicle] = veh_info['road'][0]

            else:
                if self.carwhere[vehicle] != veh_info['road'][0]:
                    road_id = veh_info['road'][0]
                    if road_id in self.road_cnt.keys():
                        self.road_cnt[road_id] += 1
                    else:
                        self.road_cnt[road_id] = 1
                    self.carwhere[vehicle] = road_id

        for vehicle in list(self.vehicle_enter_time):
            if not vehicle in vehicles:
                # print(vehicle,":",current_time,"-",self.vehicle_enter_time[vehicle])
                self.travel_time[vehicle] = current_time - self.vehicle_enter_time[vehicle]
                del self.vehicle_enter_time[vehicle]

        if done:
            pass
        else:
            pass
        
