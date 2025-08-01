window.addEventListener('DOMContentLoaded', () => {
    const map = L.map('map').setView([-1.213, 36.896], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors & CartoDB',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Global holders
    let currentLayer = null;
    let legend = null;

    function loadLayer(type) {
        const endpoint = type === 'routes' ? '/routes' : '/stops';
        const routeColors = {
            1: '#7fc97f', 2: '#beaed4', 3: '#fdc086'
        };

        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                // Clear previous map layer
                if (currentLayer) {
                    map.removeLayer(currentLayer);
                }

                // Remove legend if it exists
                if (legend) {
                    legend.remove();
                    legend = null;
                }

                if (type === 'routes') {
                    const features = data.features;
                    const routeGroup = L.layerGroup().addTo(map);
                    currentLayer = routeGroup;

                    function animateRoute(coords, color) {
                        let index = 0;
                        const routeLine = L.polyline([], {
                            color: color,
                            weight: 5,
                            opacity: 1.0
                        }).addTo(routeGroup);

                        function drawSegment() {
                            if (index < coords.length) {
                                routeLine.addLatLng(coords[index]);
                                index++;
                                setTimeout(drawSegment, 60); // animation speed
                            }
                        }

                        drawSegment();
                    }

                    features.forEach(feature => {
                        const routeId = feature.properties.route_id;
                        const color = routeColors[routeId] || 'gray';
                        const coords = feature.geometry.coordinates.map(c => [c[1], c[0]]); // [lat, lng]

                        // Animate route
                        animateRoute(coords, color);

                        // Add marker at starting point
                        const startCoord = coords[0];
                        if (startCoord) {
                            L.marker(startCoord)
                            .bindPopup(`Start of Route ${routeId}`)
                            .addTo(routeGroup);

                        }
                    });

                } else {
                    // Display stops with proportional symbols
                    currentLayer = L.geoJSON(data, {
                        pointToLayer: function (feature, latlng) {
                            const demand = feature.properties.stop_demand || 1;
                            const radius = Math.sqrt(demand) * 4;
                            return L.circleMarker(latlng, {
                                radius: radius,
                                fillColor: '#FF7F50',
                                color: '#FF7F50',
                                weight: 1,
                                opacity: 1,
                                fillOpacity: 0.7
                            });
                        },
                        onEachFeature: function (feature, layer) {
                            const stopName = feature.properties.name || 'Stop';
                            const demand = feature.properties.stop_demand || 0;
                            layer.bindPopup(`<strong>${stopName}</strong><br>Demand: ${demand}`);
                        }
                    }).addTo(map);

                    // Add legend for stop demand
                    legend = L.control({ position: 'bottomright' });
                    legend.onAdd = function (map) {
                        const div = L.DomUtil.create('div', 'info legend');
                        const grades = [1, 5, 10];
                        const scale = 4;

                        div.innerHTML += '<h4>Stop Demand</h4>';
                        grades.forEach(d => {
                            const radius = Math.sqrt(d) * scale;
                            div.innerHTML +=
                                `<div style="margin-bottom: 8px;">
                                    <svg height="${radius * 2}" width="${radius * 2}" style="vertical-align: middle;">
                                        <circle cx="${radius}" cy="${radius}" r="${radius}"
                                                fill="#FF7F50" stroke="#FF7F50" stroke-width="1" fill-opacity="0.7" />
                                    </svg>
                                    <span style="margin-left: 6px;">${d}</span>
                                </div>`;
                        });
                        return div;
                    };
                    legend.addTo(map);
                }
            })
            .catch(err => console.error(`Error loading ${type}:`, err));
    }

    loadLayer('stops');

    // Radio buttons listener
    document.querySelectorAll('input[name="map_options"]').forEach(input => {
        input.addEventListener('change', (e) => {
            loadLayer(e.target.value);
        });
    });
});
