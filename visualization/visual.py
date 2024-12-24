import numpy as np
import pandas as pd
import argparse
import os

def read(file_path):
    x = []
    index = np.arange(0, 110, 10)
    for i in index:
        x.append(pd.read_json(file_path + f'{i}.0%known.json'))
    return x

def read_txt(file):
    f = open(file)
    line = f.readline()
    lines = ""
    while line:
        line = f.readline()
        lines += line
    f.close()
    return lines

def getcolor(rate):
    color0 = '\'#CC0000\''
    color1 = '\'#FF9900\''
    color2 = '\'#B2CC00\''
    color3 = '\'#66B200\''
    color4 = '\'#009900\''
    if rate < 0:
        color = color0
    if rate >= 0 and rate < 0.04:
        color = color1
    if rate >= 0.04 and rate < 0.08:
        color = color2
    if rate >= 0.08 and rate < 0.12:
        color = color3
    if rate >= 0.12:
        color = color4
    return color

def get_inter(file_path, choose):
    out = []
    with open(file_path) as f:
        num = int(f.readline())
        for i in range(num):
            s = f.readline().split(' ')
            place = s[:2]
            place = [float(j) for j in place]
            if i in choose:
                out.append(place) 
    return out

def process_points(inter, col, head, tail):
    n_points = len(inter)
    text = head
    for i in range(n_points):
        if col.get(i) == None:
            continue
        nodes = inter[i]
        nodes[0], nodes[1] = nodes[1], nodes[0]
        c = getcolor(col[i])

        mid = """
                {
                    'type': 'Feature',
                    'properties': {
                        'color': %s
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': %s
                    }
                },   
            """%(c, nodes)
        
        text = text + mid
    text += tail
    return text, i

def plot_map(map_nm, col, points, head, tail):
    txt, _ = process_points(points, col, head, tail)
    f_html = open(map_nm, 'w')
    f_html.write(txt)
    f_html.close()
    return txt

def draw(city, wb_rate):
    x = read(f'./log/{city}/point_num/')
    head = f'./visual_points/head_{city}.txt'
    tail = './visual_points/tail.txt'
    h = read_txt(head)
    t = read_txt(tail)
    cor = get_inter(f'./roadnet/{city}.txt', range(1000000))
    x_raw = dict(x[0].sum())
    x_op = dict(x[int(wb_rate * 10)].sum())
    rate = {}
    for key in x_raw.keys():
        if x_raw[key] == 0:
            if x_op[key] == 0:
                continue
            else:
                rate[key] = 1
        else:
            rate[key] = (x_op[key] - x_raw[key]) / x_raw[key]
    log_path = f'./result/{city}/'
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    txt = plot_map(log_path + f'{city}-{int(wb_rate * 100)}.html', rate, cor, h, t)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--city', type=str, default='shanghai', help='the city that will be visualized'
    )
    parser.add_argument(
        '--wb_rate', type=float, default=0.1, help='the rate of webster method is applied'
    )
    args = parser.parse_args()
    draw(args.city, args.wb_rate)