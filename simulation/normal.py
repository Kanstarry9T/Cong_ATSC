import argparse
import gym
import multiprocessing as mp
import time
gym.logger.set_level(40)
import numpy as np
import pandas as pd
from utility.environment import TSCEnv
from utility.world import World
from metric import TravelTimeMetric, ThroughputMetric
from metric.travel_distance import TravelDistanceMetric
from metric.point_count import pointoutMetric
import os
import json
from agent.myagent_set import WebsterAgent
import configparser
import shutil
import io


def run(city_name):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--steps", type=int, default=60, help="number of steps (default: 3600)"
    )
    parser.add_argument(
        "--thread", type=int, default=8, help="number of threads (default: 8)"
    )
    parser.add_argument(
        "--action_interval",
        type=int,
        default=60,
        help="how often agent make decisions (default: 60)",
    )

    parser.add_argument(
        "--config_file", type=str, default=f"./dataset_normal/{city_name}/config.json", help="path of config file")

    parser.add_argument(
        "--engine_config_file", type=str, default=f"./dataset_normal/{city_name}/engine.cfg", help="path of config file")
    
    parser.add_argument(
        "--rate", type=str, default=str(), help="percentage of flow add to the initial flow (default: None)")

    parser.add_argument(
        "--wb_rate", type=float, default=0.0, help="percentage of intersections that uses webster method (default: None)")

    args = parser.parse_args()

    json_cfg = {"dir": f"dataset_normal/{city_name}/",
        "roadnetFile": "roadnet.txt",
	    "flowFile": f"flow{args.rate}.txt",
	    "routeFile": "None.json"
    }
    json_cfg_str = json.dumps(json_cfg, indent=4)
    with open('./dataset_normal/' + city_name + '/config.json', 'w') as json_file:
        json_file.write(json_cfg_str)
    
    conf1 = configparser.ConfigParser()
    conf2 = configparser.ConfigParser(delimiters=':')
    cfg_file = open('./dataset_normal/' + city_name + '/engine.cfg', 'w')
    conf1.set(None, 'start_time_epoch', '0')
    conf1.set(None, 'max_time_epoch', '3600')
    conf2.set(None, 'road_file_addr', f'./dataset_normal/{city_name}/roadnet.txt')
    conf2.set(None, 'vehicle_file_addr', f'./dataset_normal/{city_name}/flow{args.rate}.txt')
    conf2.set(None, 'report_log_mode', 'normal')
    conf2.set(None, 'report_log_addr', './log/')
    conf1.set(None, 'report_log_rate', '10')
    conf1.set(None, 'warning_stop_time_log', '100')
    conf2.write(cfg_file)
    conf1.write(cfg_file)
    cfg_file.close()

    with open('./dataset_normal/' + city_name + '/engine.cfg', 'w') as config_file, io.StringIO() as buffer:
        conf1.write(buffer)
        buffer.seek(0)
        buffer.readline()
        shutil.copyfileobj(buffer, config_file)

    with open('./dataset_normal/' + city_name + '/engine.cfg', 'a') as config_file, io.StringIO() as buffer:
        conf2.write(buffer)
        buffer.seek(0)
        buffer.readline()
        shutil.copyfileobj(buffer, config_file)

    config = json.load(open(args.config_file, 'r'))
    net = config['dir'].split('/')[1]
    flow = config["flowFile"].split('.')[0]
    netandflow = net + flow

    world = World(args.engine_config_file, args.config_file, thread_num=args.thread, args=args, route=False)

    dic_agents = {}

    pre_arange = []
    with open(f'./pre_known_data/trafficlight/{city_name}/pre_aran_noise.txt', 'r') as input:
        for line in input:
            tmp = line.split()
            tmp = [int(j) for j in tmp]
            pre_arange.append(tmp)

    inter = pd.read_json(f'./pre_known_data/log_normal/{city_name}/point_num/0.0%known.json')
    inter = dict(inter.sum())
    total_inter = [k for k, v in sorted(inter.items(), key=lambda item: item[1])]
    total_inter.reverse()
    inter_choose = set(total_inter[: round(args.wb_rate * len(total_inter))])

    agents = []
    inter_num = 0
    for i in world.intersections:
        action_space = gym.spaces.Discrete(4)
        pre = pre_arange[inter_num]
        if i.id in inter_choose:
            pre = None
        agents.append(WebsterAgent(i.id, action_space, i, acknowledge=True, pre=pre))
        inter_num += 1
    dic_agents["tsc"] = agents


    # create metric
    metric = [
        TravelDistanceMetric(world),
        ThroughputMetric(world),
        # pointoutMetric(world),
    ]

    # create env
    env = TSCEnv(world, dic_agents["tsc"], metric)
    t1 = time.time()
    distance_record = []
    speed_record = []
    out_num_record = []
    point_num_record = []
    dic_actions = {} 

    for i in range(args.steps):
        print("Step {} finished.".format(i))
        for t in range(args.action_interval):
            key = "tsc"
            dic_actions[key] = [agent.get_action(world) for agent in dic_agents[key]]
            _, reward, _, _ = env.step(dic_actions)
            for j in range(len(metric)):
                env.metric[j].update(done=False)

        if i != 0:
            dis, speed = env.metric[0].update(done=False)
            distance_record.append(dis)
            speed_record.append(speed)
            out_num = env.metric[1].update(done=False)
            out_num_record.append(out_num)

        # recording the number of vehicles coming out from each intersection
        '''
        if i % 5 == 4:
            point_num = env.metric[2].total_query()
            env.metric[2].reset()
            point_num_record.append(point_num)
        '''

    t2 = time.time()        
    dir_name1 = f'./log_normal_info/increse{args.rate}-webster{args.wb_rate}/'
    if not os.path.isdir(dir_name1):
        os.makedirs(dir_name1)
    record = {'distance': distance_record, 'speed': speed_record, 'throuput': out_num_record, 'runningtime': [(t2 - t1) / 60]}
    json_str = json.dumps(record, indent=2)

    with open(dir_name1 + f'{city_name}.json', 'w') as json_file:
        json_file.write(json_str)

    # recording the number of vehicles coming out from each intersection
    '''
    dir_name2 = f'./log_normal_pointout/increse{args.rate}-webster{args.wb_rate}/'
    if not os.path.isdir(dir_name2):
        os.makedirs(dir_name2)
    with open(dir_name2 + f'{city_name}.json', 'w') as output:
        json.dump(point_num_record, output)
    '''
    print(f'{city_name} done!')
        

if __name__ == "__main__":
    cities = os.listdir('./dataset_normal')
    pool = mp.Pool(25)
    pool.map(run, cities)
    pool.close()
    pool.join()
    print('All finish!')
