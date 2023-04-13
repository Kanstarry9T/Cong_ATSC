import numpy as np
from agent.base import BaseAgent

class WebsterAgent(BaseAgent):
    def __init__(self, id, action_space, intersection, S=0.67, acknowledge=True, yellow_time=4, pre=None):
        super().__init__(action_space)
        self.id = id
        self.intersection = intersection
        self.saturation_flow = S
        self.last_action = 0
        self.last_set_time = 0
        self.T = 56
        self.phase_num = 4
        self.acknowledge = acknowledge
        self.yellow_time = yellow_time
        self.current_phase = 0
        self.current_time = 1
        self.setting = []
        self.total_arangement = []
        self.pre = pre
        self.last_cl = 1
        self.mid_preflow = [0, 0, 0, 0]
        self.left_preflow = [0, 0, 0, 0] # left-turn ---> phase 
        self.left_turn_id = [[], [], [], []]
        self.mid_id = [[], [], [], []]
        self.roads = None
        self.cars = set()
        self.cnt = 0
        

    def get_action(self, world):
        if not self.intersection.signal:
            return -1

        if not self.acknowledge: # 
            if world.eng.get_current_time() - self.last_set_time < (self.T / self.phase_num):
                return self.last_action
            else:
                self.last_action += 1
                self.last_action %= self.phase_num
                self.last_set_time = world.eng.get_current_time()
                return self.last_action

        if self.pre != None:
            if self.current_phase >= len(self.pre):
                self.pre.append(self.pre[-1] + 14)

            if self.pre[self.current_phase] <= self.current_time:
                self.current_phase += 1
            self.current_time += 1
            return self.current_phase % self.phase_num
        
        if self.cnt % 29 == 0:
            self.update_flow(world=world)
        self.cnt += 1

        if len(self.setting) != 0: # a list to record phase switch time
            if self.setting[self.current_phase] <= self.current_time: # 
                self.current_phase += 1 # switch to next phase

            self.current_time += 1
            if self.current_phase < self.phase_num: # phase_num: number of phases within a signal cycle
                #print(self.current_phase)
                return self.current_phase

        self.current_time = 1
        self.current_phase = 0 # switch to next signal cycle

        y = np.zeros(4)
        #print(self.left_preflow)
        y[0] = max(self.left_preflow[0], self.left_preflow[2])
        y[2] = max(self.left_preflow[1], self.left_preflow[3])
        y[1] = max(self.mid_preflow[0], self.mid_preflow[2])
        y[3] = max(self.mid_preflow[1], self.mid_preflow[3])
        #print(y)
        self.mid_preflow = [0, 0, 0, 0]
        self.left_preflow = [0, 0, 0, 0] # initialize for updating phase flow of current signal cycle

        saturation_flow = self.saturation_flow * self.last_cl
        critical_ratio = y / saturation_flow
        lost_time = 4 * self.yellow_time
        Y = min(0.95, np.sum(critical_ratio))
        CL = round(((1.5 * lost_time) + 5) / (1.0 - Y))
        CL = min(CL, 180)
        self.setting = []
        green_effetive = CL - lost_time
        for i in range(4):
            Y = max(Y, 0.01)
            green = max(10, critical_ratio[i] * green_effetive / Y) + self.yellow_time
            '''
            if green > 200:
                print(critical_ratio)
                print(y)
                print(saturation_flow)
                print(self.last_cl)
                print('\n')
            '''    
            self.setting.append(green)

        self.total_arangement.append(self.setting) # record the signal timing 
        self.setting = np.array(self.setting).cumsum() 
        self.last_cl = self.setting[-1]
        return 0
        
    def get_reward(self):
        return 0

    def get_ob(self):
        return 0

    def get_arangement(self):
        self.arangement = np.array(self.total_arangement)
        arangement = np.round(self.arangement.reshape(-1))
        arangement = arangement.astype(np.int32)
        return arangement.cumsum()

    def update_flow(self, world):
        car_ids = world.eng.get_lane_vehicles()
        roads = world.agents[self.id][4:] # incoming approaches 4 * 3 lanes
        
        for i in range(4):
            road = roads[i] * 100
            if car_ids.get(road) != None:
                ids = car_ids[road]
                delta1 = set(self.left_turn_id[i])-set(ids)
                self.left_turn_id[i] = ids
                self.left_preflow[i] += len(delta1)
            else:
                self.left_preflow[i] += len(self.left_turn_id[i])
                self.left_turn_id[i] = []

            road += 1
            if car_ids.get(road) != None:
                ids = car_ids[road]
                delta2=set(self.mid_id[i])-set(ids)
                self.mid_id[i] = ids
                self.mid_preflow[i] += len(delta2)
            else:
                self.mid_preflow[i] += len(self.mid_id[i])
                self.mid_id[i] = []

    def update_new_cars(self, cars, world):
        if self.roads == None:
            self.roads = set(world.agents[self.id][4:])
        for car in cars:
            route = set(world.eng.get_vehicle_route(car))
            if len(route & self.roads) > 0:
                self.cars.add(car)
            
