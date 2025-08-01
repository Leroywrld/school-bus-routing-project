import sys
import os

# Add the parent directory (sbrp web map) to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# serve_map.py
from flask import Flask, jsonify, render_template
from utilis.db import psycop_connection

app = Flask(__name__, template_folder='templates')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/stops")
def get_stops():
    conn = psycop_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', jsonb_agg(
                jsonb_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(ST_Transform(stop_geometry, 4326))::jsonb,
                    'properties', to_jsonb(stops) - 'stop_geometry'
                )
            )
        )
        FROM stops;
    """)
    return jsonify(cur.fetchone()[0])


@app.route("/routes")
def get_routes():
    conn = psycop_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', jsonb_agg(
                jsonb_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(ST_Transform(route_geometry, 4326))::jsonb,
                    'properties', to_jsonb(routes) - 'route_geometry'
                )
            )
        )
        FROM routes;
    """)
    return jsonify(cur.fetchone()[0])


if __name__ == "__main__":
    app.run(debug=True)


