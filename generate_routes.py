import pandas as pd
import geopandas as gpd
import openrouteservice as ors
from geoalchemy2 import Geometry, WKTElement
import requests
from shapely.geometry import shape, LineString
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utilis.db import get_connection

vehicles_query = """
SELECT vehicle_id, vehicle_capacity, cost_per_km, start_location FROM vehicles;
"""
stops_query = """
SELECT stop_id, stop_demand, stop_geometry FROM stops;
"""

stops_gdf = gpd.read_postgis(sql=stops_query, con=get_connection(), geom_col='stop_geometry')
vehicles_gdf = gpd.read_postgis(sql=vehicles_query, con=get_connection(), geom_col='start_location')

def get_xy(gdf:gpd.GeoDataFrame, geometry_col:str):
    gdf['lon'] = list(gdf[geometry_col].x)
    gdf['lat'] = list(gdf[geometry_col].y)
    print(gdf.crs)
    print(gdf.info())
    return gdf

vehicles_gdf = get_xy(vehicles_gdf, 'start_location')
stops_gdf = get_xy(stops_gdf, 'stop_geometry')

# create a list of dictionaries containing information about jobs/stops
jobs = []
for i, row in stops_gdf.iterrows():
    jobs.append({
        "id": row['stop_id'],
        "location": [row['lon'], row['lat']],
        "amount": [row['stop_demand']]
    })

print(jobs)

# create a list of dictionaries containing information about the vehicle fleet
vehicles = []
for i, row in vehicles_gdf.iterrows():
    vehicles.append({
        "id": row['vehicle_id'],
        "profile": "driving-car",
        "start": [row['lon'], row['lat']],
        "end": [row['lon'], row['lat']],
        "capacity": [row['vehicle_capacity']],
        "costs": {
            "per_distance": row['cost_per_km']/1000
        }
    })

print(vehicles)

request_body = {
    "vehicles": vehicles,
    "jobs": jobs,
    "geometry": True,
    "metrics": ["distance", "duration"]
}

API_KEY = "5b3ce3597851110001cf624859b73e5ab74146fe9b1d191314eacbe0"
optimization_url = "https://api.openrouteservice.org/optimization"

def get_optimized_routes(api_key:str, url:str, request_body:dict):
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(url=url, json=request_body, headers=headers)
    output = response.json()

    return output

#so called optimization response
result = get_optimized_routes(api_key=API_KEY, url=optimization_url, request_body=request_body)

def extract_ordered_coords(optimization_response, job_id_to_coords):
    """
    Parameters:
        ors_response (dict): JSON response from ORS /optimization.
        job_id_to_coords (dict): Mapping of job IDs to [lon, lat] coordinates.

    """
    routes = optimization_response.get("routes", [])
    ordered_coords = {}

    for route in routes:
        vehicle_id = route["vehicle"]
        steps = route["steps"]
        coords = []

        for step in steps:
            if step["type"] == "start" or step["type"] == "end":
                coords.append(step["location"])  
            elif step["type"] == "job":
                job_id = step["id"]
                coords.append(job_id_to_coords[job_id]) 

        ordered_coords[vehicle_id] = coords

    return ordered_coords

id_coord = {0: [36.896, -1.213]}
for i, row in stops_gdf.iterrows():
    id_coord[row['stop_id']] = [row['lon'], row['lat']]
print(id_coord)

ordered_stops = extract_ordered_coords(optimization_response=result, job_id_to_coords=id_coord)

def get_route_info(coords, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

    
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    all_routes_info = {}
    for vehicle in range(1, 4):
        body = {"coordinates": coords[vehicle],
                "units": "km",
                "geometry": True
                }
        response = requests.post(url, json=body, headers=headers)
        data = response.json()
        all_routes_info[vehicle] = data
    
    return all_routes_info

#so called directions response
all_routes_info = get_route_info(coords=ordered_stops, api_key=API_KEY)

def get_steps(optimization_response):
    routes = optimization_response.get('routes', [])
    ordered_steps = {}
    for route in routes:
        vehicle_id = route['vehicle']
        steps = route['steps']
        job_ids = []

        for step in steps:
            if step['type'] == 'job':
                job_ids.append(step['id'])
        
        ordered_steps[vehicle_id] = str(job_ids).replace('[', '{').replace(']', '}')
    
    return ordered_steps

def get_route_geometry(directions_response:dict):
    geom_dict = {}
    for vehicle in range(1, 4):
        response = directions_response[vehicle]
        route_geojson = response['features'][0]['geometry']
        route_geometry = shape(route_geojson)
        geom_dict[vehicle] = route_geometry
    
    return geom_dict

def get_route_length(directions_response:dict):
    distance_dict = {}
    for vehicle in range(1, 4):
        response = directions_response[vehicle]
        route_distance = response['features'][0]['properties']['summary']['distance']
        distance_dict[vehicle] = route_distance
    
    return distance_dict

def get_duration(directions_response:dict):
    duration_dict = {}
    for vehicle in range(1, 4):
        response = directions_response[vehicle]
        route_duration = response['features'][0]['properties']['summary']['duration']
        route_duration = str(round(route_duration/60)) + " " + "minutes"
        duration_dict[vehicle] = route_duration
    
    return duration_dict

def create_routes_table(directions_response:dict, optimization_response:dict):
    route_steps = get_steps(optimization_response)
    route_length = get_route_length(directions_response)
    route_duration = get_duration(directions_response)
    route_geometry = get_route_geometry(directions_response)

    ids = []
    steps = []
    lengths = []
    durations = []
    geoms = []
    routes_dict = {}
    for vehicle in range(1, 4):
        ids.append(vehicle)
        steps.append(route_steps[vehicle])
        lengths.append(route_length[vehicle])
        durations.append(route_duration[vehicle])
        geoms.append(route_geometry[vehicle])


        routes_dict['route_id'] = ids
        routes_dict['route_steps'] = steps
        routes_dict['route_length'] = lengths
        routes_dict['route_duration'] = durations
        routes_dict['route_geometry'] = geoms
    

    gdf = gpd.GeoDataFrame(data=routes_dict, geometry='route_geometry', crs=3857)
    print(gdf.info())
    print(gdf.crs)

    return gdf

routes_table = create_routes_table(directions_response=all_routes_info, optimization_response=result)

routes_table.to_postgis(name='routes', con=get_connection(), if_exists='append', index=False)

