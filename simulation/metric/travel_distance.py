import numpy as np


class TravelDistanceMetric():
    def __init__(self, world):
        self.world = world
        self.world.subscribe(["vehicles", "time"])
        self.vehicle_last_road_dis = {}
        self.vehicle_last_dis = {}
        self.vehicle_last_place = {}
        self.vehicle_enter_time = {}
        self.travel_dis = 0
        self.travel_time = 0
        # self.speed = 0
        self.num = 0

    def reset(self):
        self.vehicle_last_dis = {}
        self.travel_dis = 0
        # self.speed = 0
        self.num = 0

    def update(self, done=False):
        vehicles = self.world.get_info("vehicles")
        current_time = self.world.get_info("time")
        dis_add = 0
        # speed_add = 0
        time_add = 0

        for vehicle in vehicles:
            if self.vehicle_enter_time.get(vehicle) == None:
                self.vehicle_enter_time[vehicle] = current_time

        for vehicle in vehicles:
            veh_info = self.world.eng.get_vehicle_info(vehicle)
            if self.vehicle_last_dis.get(vehicle) == None:
                self.vehicle_last_dis[vehicle] = veh_info['distance'][0]
                self.vehicle_last_place[vehicle] = veh_info['road'][0]
            else:
                if self.vehicle_last_place[vehicle] == veh_info['road'][0]:
                    self.vehicle_last_dis[vehicle] += veh_info['distance'][0] - self.vehicle_last_road_dis[vehicle]
                else:
                    self.vehicle_last_dis[vehicle] += veh_info['distance'][0]
                    self.vehicle_last_place[vehicle] = veh_info['road'][0]
            dis_add += self.vehicle_last_dis[vehicle]
            # speed_add += self.vehicle_last_dis[vehicle] / (current_time - self.vehicle_enter_time[vehicle] + 1)
            time_add += current_time - self.vehicle_enter_time[vehicle] + 1
            self.vehicle_last_road_dis[vehicle] = veh_info['distance'][0]

        vehicles = set(vehicles)
        for vehicle in list(self.vehicle_last_dis):
            if vehicle not in vehicles:
                self.travel_dis += self.vehicle_last_dis[vehicle]
                self.travel_time += current_time - self.vehicle_enter_time[vehicle]
                # self.speed += self.vehicle_last_dis[vehicle] / (current_time - self.vehicle_enter_time[vehicle])
                self.num += 1
                del self.vehicle_last_dis[vehicle]
                del self.vehicle_enter_time[vehicle]

        
        if self.num == 0:
            return 0, 0
        else:
            return (self.travel_dis + dis_add) / (self.num + len(vehicles)), (self.travel_dis + dis_add) / (self.travel_time + time_add)
