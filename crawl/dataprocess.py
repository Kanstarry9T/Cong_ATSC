import numpy as np
import pandas as pd
import argparse
import os

def get(log, mod):
    dfs = []
    folders = os.listdir(log)
    if mod == 'rush':
        t1, t2 = '07', '08'
    else:
        t1, t2 = '12', '13'
    for folder in folders:
        files = os.listdir(log + folder)
        for file in files:
            if file[:2] == t1 or file[:2] == t2:
                dfs.append(pd.read_csv(log + folder + '//' + file))
    res = {}
    std = {}
    length = len(dfs)
    for i in range(length):
        for j in range(100):
            if res.get(dfs[i]['label'][j]) == None:
                res[dfs[i]['label'][j]] = dfs[i]['realSpeed'][j] / length
                std[dfs[i]['label'][j]] = [dfs[i]['realSpeed'][j]]
            else:
                res[dfs[i]['label'][j]] += dfs[i]['realSpeed'][j] / length
                std[dfs[i]['label'][j]].append(dfs[i]['realSpeed'][j])
    for city in std.keys():
        res[city] = [res[city]]
        res[city].append(np.std(std[city]))
    return res

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mod", type=str, default='rush', help="process what kind of real flow speed data"
    )
    args = parser.parse_args()

    rest = get('./log/', mod=args.mod)
    df_rest = pd.DataFrame.from_dict(rest, orient='index', columns=['speed', 'speed_std'])
    df_rest.to_excel(f'./{args.mod}.xlsx')