import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
from geoalchemy2 import Geometry, WKTElement
import sys
import os

# Add the parent directory (sbrp web map) to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utilis.db import get_connection                        

# paths to various kml files containing stops data
mirema_path = "C:\\Users\\ADMIN\\OneDrive\\Desktop\\Final Year Project\\data\\stops\\Mirema.kml"
thika_road_path = 'C:\\Users\\ADMIN\\OneDrive\\Desktop\\Final Year Project\\data\\stops\\Thika Road.kml'
kasarani_path = 'C:\\Users\\ADMIN\\OneDrive\\Desktop\\Final Year Project\\data\\stops\\Kasarani.kml'
school_path = 'C:\\Users\\ADMIN\\OneDrive\\Desktop\\Final Year Project\\data\\stops\\school.kml'

#read the data from disk
mirema_stops = gpd.read_file(mirema_path)
thika_rd_stops = gpd.read_file(thika_road_path)
kasarani_stops = gpd.read_file(kasarani_path)
school = gpd.read_file(school_path)

#columns to keep in the geodataframe
columns = ['Name', 'stop_geometry']

# function to clean geometries, rename columns and reproject crs in the geodataframes
def transform_data(gdf:gpd.GeoDataFrame, target_crs:int, columns:list):
    gdf['geometry'] = gpd.GeoSeries(gpd.points_from_xy(x=gdf['geometry'].x, y=gdf['geometry'].y))
    gdf = gdf.set_crs(epsg=target_crs, allow_override=True)
    gdf = gdf.rename_geometry(col='stop_geometry')
    gdf = gdf[columns]
    print(gdf.crs)
    print(gdf.info())
    return gdf

# transformed geodataframes
mirema_stops = transform_data(gdf=mirema_stops, target_crs=3857, columns=columns)
thika_rd_stops = transform_data(gdf=thika_rd_stops, target_crs=3857, columns=columns)
kasarani_stops = transform_data(gdf=kasarani_stops, target_crs=3857, columns=columns)

# function 
def random_positive_integer_partition(n, m, seed=None):
    #n is the number of partions while m is the total sum
    if m < n:
        raise ValueError("Impossible to partition: sum m must be at least n.")
    
    rng = np.random.default_rng(seed)
    
    remaining = m - n
    
    # Use np.arange instead of range!
    cuts = np.sort(rng.choice(np.arange(1, remaining + n), n - 1, replace=False))
    
    cuts = np.concatenate(([0], cuts, [remaining + n]))
    
    partition = np.diff(cuts) - 1
    partition += 1
    
    return partition

def attach_stop_demand(gdf:gpd.GeoDataFrame, n_stops:int, total_demand:int):
    demand_array = random_positive_integer_partition(n=n_stops, m=total_demand, seed=8)
    gdf['stop_demand'] = demand_array
    print(f"sum of demand values equals: {np.sum(demand_array)}")
    print(gdf.info())
    return gdf

# general route information
gen_route_info = {
    'mirema': {'n_stops': 26,
               'total_demand': 41},
    'thika_rd': {'n_stops': 8,
                 'total_demand': 17},
    'kasarani': {'n_stops': 21, 'total_demand': 49}
}

#assigning demand values to stops in the various routes
mirema_stops = attach_stop_demand(gdf=mirema_stops, n_stops=gen_route_info['mirema']['n_stops'], total_demand=gen_route_info['mirema']['total_demand'])
thika_rd_stops = attach_stop_demand(gdf=thika_rd_stops, n_stops=gen_route_info['thika_rd']['n_stops'], total_demand=gen_route_info['thika_rd']['total_demand'])
kasarani_stops = attach_stop_demand(gdf=kasarani_stops, n_stops=gen_route_info['kasarani']['n_stops'], total_demand=gen_route_info['kasarani']['total_demand'])

def concatentate_stops(list_gdfs:list):
    all_stops = pd.concat(list_gdfs, ignore_index=True)
    all_stops = all_stops[['stop_demand', 'stop_geometry']]
    print(all_stops.crs)
    print(all_stops.info())
    return all_stops

gdfs = [mirema_stops, thika_rd_stops, kasarani_stops]
stop_data = concatentate_stops(list_gdfs=gdfs)

#a dictionary containing information about the fleet of vehicles involved
vehicle_info = {
    'vehicle_id': [1, 2, 3],
    'vehicle_capacity': [33, 18, 51],
    'cost_per_km': [0.182, 0.130, 0.204],
    'start_location': [Point(36.896, -1.213), Point(36.896, -1.213), Point(36.896, -1.213)],
    'end_location': [Point(36.896, -1.213), Point(36.896, -1.213), Point(36.896, -1.213)]
}

vehicle_data = gpd.GeoDataFrame(data=vehicle_info, crs=3857, geometry='start_location')

vehicle_data = vehicle_data.set_geometry(col='end_location', crs=3857)
print(vehicle_data.info())

#load data to db
stop_data.to_postgis('stops', con=get_connection(), if_exists='append')
vehicle_data.to_postgis(name='vehicles', con=get_connection(), if_exists='append', index=False)