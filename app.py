from flask import Flask, render_template_string, send_file, request, render_template
from collections import deque
import networkx as nx
import matplotlib.pyplot as plt
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import googlemaps
import json
import requests
import matplotlib
matplotlib.use('Agg')


app = Flask(__name__)

# Given graph
import json

# Replace 'YOUR_API_KEY' with your actual Google Maps API key
gmaps = googlemaps.Client(key='AIzaSyAkrFYkxmtHZHod1Xd2b7OkGFsnto59oyQ')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save_points', methods=['POST'])
def save_points():
    data = request.get_json()

    with open('points.json', 'w') as f:
        json.dump(data,f)
    
    distances = calculate_distances(data)
    with open('distances.json', 'w') as f:
        json.dump(distances, f)
    return jsonify({'message': 'Distances saved successfully!'})

def calculate_distances(data):
    distances = {}
    for i, point1 in enumerate(data):
        distances[chr(ord('A') + i)] = {}
        origin = (point1['lat'], point1['lng'])
        for j, point2 in enumerate(data):
            destination = (point2['lat'], point2['lng'])
            if i != j:  # Avoid calculating distance to itself
                intermediate_point = None
                for k, intermediate in enumerate(data):
                    if i != k != j:
                        if is_point_between(point1, point2, intermediate):
                            intermediate_point = (intermediate['lat'], intermediate['lng'])
                            break
                if not intermediate_point:
                    result = gmaps.distance_matrix(origin, destination, mode='driving')
                    distance = result['rows'][0]['elements'][0]['distance']['value']  # Distance in meters
                    distances[chr(ord('A') + i)][chr(ord('A') + j)] = distance
    return distances

def is_point_between(point1, point2, intermediate):
    lat1, lng1 = point1['lat'], point1['lng']
    lat2, lng2 = point2['lat'], point2['lng']
    lat_inter, lng_inter = intermediate['lat'], intermediate['lng']
    return min(lat1, lat2) <= lat_inter <= max(lat1, lat2) and min(lng1, lng2) <= lng_inter <= max(lng1, lng2)


def bfs(graph, start, end):
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        if node == end and len(set(graph.keys()) - set(path)) == 0:
            return path
        for neighbor in graph[node]:
            queue.append((neighbor, path + [neighbor]))

# Drawing the graph
def draw_graph(graph):
    G = nx.Graph()

    for node, edges in graph.items():
        for edge, weight in edges.items():
            G.add_edge(node, edge, weight=weight)

    pos = nx.spring_layout(G)
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw(G, pos, with_labels=True)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    plt.axis('off')

    img_path = f'static/graph_{datetime.now().strftime("%Y%m%d%H%M%S")}.png'
    plt.savefig(img_path, format='png')
    plt.clf()
    plt.close()

    return img_path


@app.route('/result',  methods=['GET', 'POST'])
def result():
    with open('points.json', 'r') as file:
        coordinates = json.load(file)

    with open('distances.json', 'r') as file:
        graph = json.load(file)

    # Extract coordinates data from the form
    start_node = "A"
    end_node = "A"
    img_path = draw_graph(graph)

    # List of nodes
    nodes = sorted(graph.keys())

    # Render the template with nodes, default start node, and default end node
    return render_template('result.html', nodes=nodes,img_path=img_path,coordinates=coordinates)


@app.route('/update_path', methods=['POST'])
def update_path():
    with open('distances.json', 'r') as file:
        graph = json.load(file)

    data = request.get_json()
    start_node = data['startNode']
    end_node = data['endNode']

    # Find the shortest path
    shortest_path = bfs(graph, start_node, end_node)
    print(shortest_path)

    # Calculate distance
    distance = sum(graph[node][shortest_path[i+1]] for i, node in enumerate(shortest_path[:-1]))

    # Shortest path information
    shortest_path_info = f"Shortest Path: {'->'.join(shortest_path)} <br> Distance: {distance}"

    return jsonify({'shortest_path_info': shortest_path_info, "shortest_path":shortest_path})

@app.route('/route', methods=['POST'])
def route():
    data = request.json
    start = data['start']
    end = data['end']
    
    api_key = 'AIzaSyAkrFYkxmtHZHod1Xd2b7OkGFsnto59oyQ'  
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start}&destination={end}&key={api_key}"
    response = requests.get(url)
    directions = response.json()
    
    if directions['status'] == 'OK':
        route = directions['routes'][0]['overview_polyline']['points']
        return jsonify({'route': route})
    else:
        return jsonify({'error': 'Route not found'}), 404

if __name__ == "__main__":
    app.run(debug=True)
