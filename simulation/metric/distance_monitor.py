from . import BaseMetric
import numpy as np


class TravelMonitor():
    """
    Calculate average travel time of all vehicles.
    For each vehicle, travel time measures time between it entering and leaving the roadnet.
    """

    def __init__(self, world):
        self.world = world
        self.world.subscribe(["vehicles", "time"])
        self.vehicle_enter_time = {}
        self.travel_time = {}
        self.travel_dis = 0

        self.carwhere = {}
        self.carrun={}

        self.vehicle_enter_road_time = {}

        #count for road
        self.road_car_n={}
        self.road_car_s={}

        # for cars in mid-road
        self.mark_in_road={}
        self.in_road_dis={}
        self.in_road_time={}


    def reset(self):
        self.travel_dis = 0
        self.vehicle_enter_time = {}
        self.travel_time = {}
        self.carwhere={}
        self.carrun={}
        self.vehicle_enter_road_time = {}
        self.road_car_n = {}
        self.road_car_s = {}
        self.mark_in_road = {}
        self.in_road_dis = {}
        self.in_road_time = {}

    def restart(self):

        current_time = self.world.get_info("time")
        self.road_car_n = {}
        self.road_car_s = {}
        self.mark_in_road = {}
        self.in_road_dis = {}
        self.in_road_time = {}

        # prepare for the cars in the mid-road

        for vehicle in list(self.vehicle_enter_time):
            self.mark_in_road[vehicle] = True
            self.in_road_dis[vehicle] = self.carrun[vehicle]
            self.in_road_time[vehicle] = current_time

    def total_query(self):
        current_time = self.world.get_info("time")
        vehicles = self.world.get_info("vehicles")
        query_set = {}

        for vehicle in list(self.vehicle_enter_time):
            road_id = self.carwhere[vehicle]
            if road_id in self.road_car_s.keys():

                if vehicle in self.mark_in_road.keys():
                    if current_time > self.in_road_time[vehicle]:
                        self.road_car_s[road_id] += (self.carrun[vehicle] - self.in_road_dis[vehicle])
                        self.road_car_n[road_id] += 1
                else:
                    if current_time > self.vehicle_enter_road_time[vehicle]:
                        self.road_car_s[road_id] += self.carrun[vehicle]
                        self.road_car_n[road_id] += 1
            else:
                if vehicle in self.mark_in_road.keys():
                    if current_time > self.in_road_time[vehicle]:
                        self.road_car_s[road_id] = (self.carrun[vehicle] - self.in_road_dis[vehicle])
                        self.road_car_n[road_id] = 1
                else:
                    if current_time > self.vehicle_enter_road_time[vehicle]:
                        self.road_car_s[road_id] = self.carrun[vehicle]
                        self.road_car_n[road_id] = 1

        for road_id in self.road_car_s.keys():
            query_set[road_id]= self.road_car_s[road_id]

        return query_set

    def query(self,road_id):
        current_time = self.world.get_info("time")

        q_s = 0
        q_n = 0

        if road_id in self.road_car_s.keys():
            q_s = self.road_car_s[road_id]
            q_n = self.road_car_n[road_id]

        for vehicle in list(self.vehicle_enter_time):
            if self.carwhere[vehicle] == road_id:
                if vehicle in self.mark_in_road.keys():
                    if current_time>self.in_road_time[vehicle]:
                        q_s += (self.carrun[vehicle]-self.in_road_dis[vehicle])
                        q_n += 1
                else:
                    if current_time>self.vehicle_enter_road_time[vehicle]:
                        q_s += self.carrun[vehicle]
                        q_n += 1
        if q_n == 0:
            return 0
        return q_s



    def update(self, done=False):


        vehicles = self.world.get_info("vehicles")

        current_time = self.world.get_info("time")

        for vehicle in vehicles:
            veh_info = self.world.eng.get_vehicle_info(vehicle)

            if not vehicle in self.vehicle_enter_time:

                self.vehicle_enter_time[vehicle] = current_time
                self.carwhere[vehicle]=veh_info['road'][0]
                self.vehicle_enter_road_time[vehicle] = current_time
                self.carrun[vehicle]=veh_info['distance'][0]

            else:
                if self.carwhere[vehicle] != veh_info['road'][0]:
                    road_id = self.carwhere[vehicle]

                    if vehicle in self.mark_in_road.keys():
                        car_v=(self.carrun[vehicle]-self.in_road_dis[vehicle])
                        del self.mark_in_road[vehicle]
                    else:
                        car_v=self.carrun[vehicle]

                    if road_id in self.road_car_s.keys():
                        self.road_car_s[road_id] += car_v
                        self.road_car_n[road_id] += 1
                    else:
                        self.road_car_s[road_id] = car_v
                        self.road_car_n[road_id] = 1

                    self.carwhere[vehicle]=veh_info['road'][0]
                    self.carrun[vehicle] = veh_info['distance'][0]
                    self.vehicle_enter_road_time[vehicle] = current_time

                else:
                    self.carrun[vehicle]=veh_info['distance'][0]





        for vehicle in list(self.vehicle_enter_time):

            if not vehicle in vehicles:
                road_id = self.carwhere[vehicle]
                if vehicle in self.mark_in_road.keys():
                    car_v = (self.carrun[vehicle] - self.in_road_dis[vehicle])

                else:
                    car_v = self.carrun[vehicle]

                if road_id in self.road_car_s.keys():
                    self.road_car_s[road_id] += car_v
                    self.road_car_n[road_id] += 1
                else:
                    self.road_car_s[road_id] = car_v
                    self.road_car_n[road_id] = 1

                del self.vehicle_enter_time[vehicle]
                del self.carrun[vehicle]
                del self.carwhere[vehicle]
                del self.vehicle_enter_road_time[vehicle]


        if done:
            pass
        else:
            pass

