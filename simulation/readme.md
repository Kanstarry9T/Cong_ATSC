
## Prerequesites
- Docker
- Python 3.8

## Getting Started

### Generation of flow

#### What you need for generation
- The roadnet data of the city i.e. `roadnet.txt`
- The city paramters
  - Population
  - Population density
  - Area size
- The amount of trips you want to generate

#### How to start generation
The data required should be aranged in the form below.
```
./generator/<city name>/roadnet.txt
```  
As for the following paramters of the generation.
- Poplation
- Population density
- Area size
  
You may use your custom data by modifiying file `citylist.xlsx`, which will be read while running `tripGenerator.py`. You may start generation by running the following command.
```
python tripGeneration.py
```
After generation, the flow data `flow.txt` and the information of flows `info.json` for each city will be stored in `./generator/<city name>`. After generating the flow data, you may test them by following our simulation process.

### Docker Installation
Make a CBEngine environment. Install CBEngine 0.0.1 with https://cbengine-documentation.readthedocs.io/en/latest/content/install.html Follow the installation guide and create a docker container with a conda environment named CBLab. Note that you are also required to install package `multiprocessing` as we used it to speed up simulation.

Then copy simulation part of this respository to your docker container.
```
docker cp -r ./simulation CONTAINER:/
```

### Running simulation code with docker
#### Start docker
Start docker container and enter the the project directory
```
docker exec -it CONTAINER bash
cd simulation
```
#### Datasets
The dataset `/simulation/dataset_rush/<city name>/` contains the following part. All the data are generated using the data generator that we had mentioned in the first part.
- roadnet.txt
The city's roadnet data, containing information of roads, intersections and lanes.
- flow.txt
The traffic flow that is close to the real-world speed data from 7 a.m. to 9 a.m.. In the form of starting time, end time, interval and road ids in the route for each route.
- flow`NUM`.txt
The traffic flow that adds `NUM %` more vehicles to `flow.txt`, the format is the same with `flow.txt`

Note that `config.json` and `engine.cfg` are generated during running the code, there's no need to worry about them.
It's the same format with `/dataset_normal`, which simulated traffic flow for each city from 12 a.m. to 2 p.m.

#### Testing
If you follow the installation guide of CBEngine, activate conda environment.
```
conda actiavte cblab
```
Otherwise activate your environment that installs all the required packages. Then run the code by the following command, it's the same with `normal.py`.
```
python rush.py --rate <increase flow rate> --wb_wate <rate of traffic lights that use Webster method>
```
Note that parameter `rate` is a integer (if it's empty then the code will run on `flow.txt`) while `wb_rate` is a float number. Also, the second line in the main function of `rush.py` dicides how many tasks will run in parallel.
```python
if __name__ == "__main__":
    cities = os.listdir('./dataset_rush')
    pool = mp.Pool(25)
    pool.map(run, cities)
    pool.close()
    pool.join()
    print('All finish!')
```
Currently it's set to be 25, you may change it according to your own CPU's ability and it's recommended to be set smaller than or equal to the number of logic cores of your CPU. All the output can be copied from docker container by running the command.
```
docker cp -r CONTAINER:/simulation/log_rush ./
```

### Visualization
We recorded 6 city's intersection traffic infomation for visualization. Firstly, activate a conda environment as soon as it has installed `numpy` and `pandas`. Run the following command to get a html result of the intersection flow condition in different rate of Webster method applied to traffic lights.
```
cd visualization
python visual.py --city <city name> --wb_rate <rate of traffic lights that use Webster method>
```
The output of the code will be stored in `/visualization/result/<city name>`, you may open it with your web browser.

### Spider Gaode data
Running the code requires the installation of `schedule` and `selenium`, you're also required to install `Chromedriver` and `Chrome`.
```
python gaode.py
```
This script will download the actual time speed information of 100 cities in China from Gaode every 10 minutes from 6 a.m. to 10 p.m. everyday after it's activated. The output will be stored in `/log/<date>`. We also offered a data process program to analyze the mean and std of the spidered data, you may run the code by the following command.
```
python dataprocess.py --mod <rush or normal>
```
Note that `mod` decides the time range of the speed data that is analyzed, `rush` analyzes data from 7 a.m. to 9 a.m. while `normal` analyzes data from 12 a.m to 2 p.m.. The result will be saved as `rush.xlsx` or `normal.xlsx`.