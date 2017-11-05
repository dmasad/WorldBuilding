# World Building

Generate a fantasy-style world map and history using several connected models in sequence. To see the overall output, see the [Model demo](Model demo.ipynb) Jupyter notebook.

### TerrainGenerator.py

Create the terrain, modeled as a set of Voronoi patches with elavation, and water running between the vertices eroding rivers. Almost entirely adapted from [Martin O'Leary](https://twitter.com/mewo2)'s superb C[reating Fantasy Maps](http://mewo2.com/notes/terrain/) tutorial.

### NomadModel.py

Agent-based model of nomadic tribes wandering the world in search of the best terrain. Right now this is a mostly simple way to place the cities (which are placed wherever the tribes end up), but I'd like to add a lot more to it.

### TributeModel.py

An implementation of the [Axelrod Tribute Model](http://www-personal.umich.edu/~axe/research/Building.pdf), a classic agent-based model from political science of how simple behavioral rules lead to the emergence of things like stable political coalitions, and imperial overreach leading to collapse. This is used to simulate wars betweeen the cities.

### TributeNarrative.py

Attempt at a simple model to extract historical narrative from the Tribute Model logs. For each actor, it finds the local extrema in the time series of its wealth (the key resource in the Tribute Model) and uses them to divide the history of that actor into eras. It then characterizes the era as one of growth or decline, and lists the key events (wars fought in, tribute paid or received) during that era.

