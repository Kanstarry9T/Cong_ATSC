import numpy as np
import pandas as pd
import os


def add_noise(file_path, loudness=7, random_state=42):
    np.random.seed(random_state)

    with open(file_path + 'pre_aran.txt', 'r') as f:
        data = f.read().split('\n')

    output = []
    for i in range(len(data)):
        tmp = np.array(data[i].split()).astype(np.int16)
        noise = loudness * np.random.randn(tmp.shape[0])
        tmp += noise.astype(np.int16)
        for i in range(tmp.shape[0] - 1):
            while tmp[i] <= 0:
                tmp[i] += 1
            while tmp[i+1] <= tmp[i]:
                tmp[i+1] += 1
        output.append(list(tmp))

    with open(file_path + 'pre_aran_noise.txt', 'w') as f:
        for row in output:
            for r in row:
                f.write(str(r) + ' ')
            f.write('\n')

if __name__=='__main__':
    city_df = pd.read_excel('./noisedata.xlsx')
    citylist = city_df['city_en']
    noise = city_df['STD_final']
    i = 0
    for city in citylist:
        city_dir = f'./pre_known_data/{city}/'
        add_noise(city_dir, loudness=noise[i])
        i += 1
        print(f'{city} done!')
