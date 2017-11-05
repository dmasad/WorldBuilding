'''
Map Generator
======================================

Mostly adapted from Martin O'Leary's writeup on terrain generation 
(http://mewo2.com/notes/terrain/) and the accompanying code. When it diverges,
it's probably because I couldn't quite understand the original.
'''

import numpy as np
from scipy.spatial import Voronoi
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


# Helper methods

def find_centroid(points):
    '''
    Find the centroid for a set of points.
    '''
    x_pts = [p[0] for p in points]
    y_pts = [p[1] for p in points]
    return [sum(x_pts)/len(points), sum(y_pts)/len(points)]

def lloyd_relaxation(points, x_lim=None, y_lim=None):
    '''
    Replace each point with the centroid of its Voronoi polygon.

    Args:
        points:
        x_lim, y_lim:

    Returns:
        numpy array of lloyd-relaxed points; wherever a relaxed point goes
        off the edge of the limits or is part of a polygon with ridges that
        go to infinity, the original point is included instead.

    TODO: Figure out how to have the Voronoi tesselation clip to the limit box.
    '''
    
    def check_coord(coord):
        '''Check whether a point is within the bounding box
        '''
        if x_lim is None or y_lim is None:
            return True
        return ((x_lim[0] < coord[0] < x_lim[1]) 
                and (y_lim[0] < coord[1] < y_lim[1]))
    
    voronoi = Voronoi(points)
    new_points = []
    for i, point in enumerate(voronoi.points):
        region = voronoi.regions[voronoi.point_region[i]]
        if len(region) == 0 or -1 in region:
            new_points.append(point)
        else:
            polygon = voronoi.vertices[region]
            new_pt = find_centroid(polygon)
            if check_coord(new_pt):
                new_points.append(new_pt)
            else:
                new_points.append(point)

    new_points = np.array(new_points)
    return new_points

# Map component classes
# =============================================

class Vertex:
    def __init__(self, name, coords, height=0):
        self.name = name
        self.coords = coords
        self.neighbors = set() # Adjacent vertices
        self.patches = set()  # Adjacent patches
        self.ridges = {}
        self.height = height
        self.flux = 1
    
    def add_neighbor(self, neighbor, ridge):
        self.neighbors.add(neighbor)
        self.ridges[neighbor.name] = ridge
    
    @property
    def coord_tuple(self):
        return (self.coords[0], self.coords[1])
    
    def dist(self, other):
        '''Euclidian distance to other point.
        '''
        if isinstance(other, Vertex):
            other = other.coords
        return np.linalg.norm(self.coords - other)

class Ridge:
    def __init__(self, name, end_1, end_2):
        self.name = name
        self.end_1 = end_1
        self.end_2 = end_2
        self.patches = set()
        
        end_1.add_neighbor(end_2, self)
        end_2.add_neighbor(end_1, self)

        
        self.flux = 0
    
    @property
    def line_segment(self):
        return [self.end_1.coord_tuple, self.end_2.coord_tuple]
    
    @property
    def length(self):
        return self.end_1.dist(self.end_2)
    
    @property
    def slope(self):
        delta_h = abs(self.end_1.height - self.end_2.height)
        return delta_h / self.length

class Patch:
    def __init__(self, name, vertices):
        self.name = name
        self.vertices = vertices
        self.neighbors = {} # Ridge-to-neighbor dictionary.
        for vertex in self.vertices:
            vertex.patches.add(self)
        self.centroid = find_centroid([v.coords for v in self.vertices])

        # Properties computed once the first time they're looked up, and then
        # cache for future lookup. This assumes that once we're looking up
        # patch attributes, the terrain generation itself is over.
        self._h = None 
        self._slope = None
    
    @property
    def coords(self):
        return [v.coords for v in self.vertices]
    
    @property
    def height(self):
        if self._h is None:
            self._h = min([v.height for v in self.vertices])
        return self._h
        #return np.median([v.height for v in self.vertices])
        #return np.mean([v.height for v in self.vertices])

    @property
    def slope(self):
        if self._slope is None:
            max_v = max(self.vertices, key=lambda v: v.height)
            min_v = min(self.vertices, key=lambda v: v.height)
            self._slope = (max_v.height - min_v.height) / max_v.dist(min_v)
        return self._slope
    
    def draw(self, ax, color='b', alpha=1):
        ax.fill(*zip(*self.coords), color=color, alpha=alpha)


class World:
    def __init__(self, points, x_lim=(0, 1), y_lim=(0, 1)):
        self.points = points
        self.voronoi = Voronoi(points)
        self.vertices = []
        self.ridges = {}
        self.patches = {}
        self._land_patches = []
        self._patch_network = None
        
        self.x_lim = x_lim
        self.y_lim = y_lim
        
        self.sea_level = 0
        
        self._make_vertices()
        self._make_ridges()
        self._make_patches()
        self._make_neighbors()


    def _make_vertices(self):
        for i, pt in enumerate(self.voronoi.vertices):
            v = Vertex(i, pt)
            self.vertices.append(v)

    def _make_ridges(self):
        for i, points in enumerate(self.voronoi.ridge_vertices):
            if -1 in points:
                continue
            k, j = points
            end_1 = self.vertices[k]
            end_2 = self.vertices[j]
            ridge = Ridge(i, end_1, end_2)
            self.ridges[i] = ridge

    def _make_patches(self):
        for i, region in enumerate(self.voronoi.regions):
            if -1 in region or len(region) == 0:
                continue
            patch_vertices = [self.vertices[v] for v in region]
            patch = Patch(i, patch_vertices)
            self.patches[i] = patch

    def _make_neighbors(self):
        '''
        Set up neighboring patches.
        '''
        for ridge in self.ridges.values():
            neighbors = ridge.end_1.patches.intersection(ridge.end_2.patches)
            if len(neighbors) < 2:
                continue
            p1, p2 = neighbors
            p1.neighbors[ridge] = p2
            p2.neighbors[ridge] = p1
            ridge.patches.add(p1)
            ridge.patches.add(p2)
    
    def set_heights(self, h=1.0):
        '''Set all vertices to the same height.
        '''
        for v in self.vertices:
            v.height = h

    def normalize_heights(self):
        '''Renormalize all heights to between 0 and 1.
        '''
        heights = [v.height for v in self.vertices]
        min_h = min(heights)
        max_h = max(heights)
        for v in self.vertices:
            v.height = (v.height - min_h) / (max_h - min_h) 
    
    def add_slope(self, magnitude=None, slope=None, normalize=False):
        '''Create a slope across the entire terrain.
        '''
        if slope is None:
            slope = slope = np.random.random(2) - 0.5
            slope /= np.linalg.norm(slope)
        if magnitude:
            slope *= magnitude
            
        for v in self.vertices:
            if self._check_coord(v.coords):
                v.height = np.dot(v.coords, slope)
        if normalize:
            self.normalize_heights()
    
    def add_hill(self, hill=None, r=0.5, normalize=False):
        '''Add a hill to terrain at point hill.
        '''
        if hill is None:
            hill = np.random.random(2)
        for v in self.vertices:
            if self._check_coord(v.coords):
                h = np.exp(-v.dist(hill)**2/(2*r**2)) ** 2
                v.height += h
        if normalize:
            self.normalize_heights()
    
    def make_rivers(self):
        self.reset_rivers()
        vertices_by_height = sorted(self.vertices, 
                                    key=lambda x: x.height, 
                                    reverse=True)
        
        for v in vertices_by_height:
            if not self._check_coord(v.coords): continue
            lowest = min(v.neighbors, key=lambda x: x.height)
            if lowest.height < v.height:
                lowest.flux += v.flux
                v.ridges[lowest.name].flux += v.flux
                
    def erode_heights(self, max_total=500, drop_factor=0.1):
        
        for ridge in self.ridges.values():
            if ridge.flux == 0: continue
            river = np.sqrt(ridge.flux) * ridge.slope
            creep = ridge.slope ** 2
            total = 1000*river + creep
            total = min(total, max_total)

            low_v = min([ridge.end_1, ridge.end_2], 
                        key=lambda x: x.height)
            low_v.height -= 0.1 * total / 500
    
    def set_sea_level(self, sea_level):
        '''Set the sea level for the world.
        
        Args:
            sea_level: If < 1, treated as the sea level itself;
                       if >1, treated as the percentile
        '''
        if sea_level < 1:
            self.sea_level = sea_level
        else:
            heights = [v.height for v in self.vertices]
            self.sea_level = np.percentile(heights, sea_level)

    @property
    def land_patches(self):
        '''
        List of patches above sea level.
        '''
        if len(self._land_patches) == 0:
            self._land_patches = [p for p in self.patches.values() 
                                  if p.height > self.sea_level]
        return self._land_patches
    
    def clean_coastline(self, epsilon=0.01):
        for v in self.vertices:
            neighbor_heights = np.array([n.height for n in v.neighbors])
            if (v.height < self.sea_level 
                    and sum(neighbor_heights > self.sea_level)>1):
                v.height = self.sea_level + epsilon
            elif (v.height > self.sea_level and 
                  sum(neighbor_heights < self.sea_level)>1):
                v.height = self.sea_level - epsilon
                
    def reset_rivers(self):
        for v in self.vertices:
            v.flux = 1/len(self.vertices)
        for ridge in self.ridges.values():
            ridge.flux = 0
    
    def _check_coord(self, coord):
        x, y = coord
        return ((self.x_lim[0] < x < self.x_lim[1]) 
                and (self.y_lim[0] < y < self.y_lim[1]))

    def draw_world(self, size=(8,8), river_cutoff=0.15, sea_level=None,
               show_ridges=False, ax=None, cmap=None, return_fig=False):
        if ax is None:
            fig, ax = plt.subplots(figsize=size)
        if cmap is None:
            cmap = plt.get_cmap('gist_earth')
        
        # Draw cell borders
        if show_ridges:
            line_segments = [r.line_segment for r in self.ridges.values()]
            lc = LineCollection(line_segments, linewidths=0.5, colors='k')
            ax.add_collection(lc)
        
        if sea_level is None:
            sea_level = self.sea_level
        
        # Draw rivers
        river_segments = [r.line_segment for r in self.ridges.values()
                     if (r.flux > river_cutoff and 
                    min(r.end_1.height, r.end_2.height)>sea_level)]
        lc = LineCollection(river_segments, linewidths=1, colors='steelblue')
        ax.add_collection(lc)
        
        # Draw patches
        for patch in self.patches.values():
            #if np.any(np.array([v.height for v in patch.vertices])<sea_level):
            if patch.height < sea_level:
                c = 'steelblue'
            else:
                c = cmap(patch.height)
            patch.draw(ax, c)
        
        ax.set_xlim(self.x_lim)
        ax.set_ylim(self.y_lim)
        ax.axis('off')
        if return_fig:
            return fig

    @property
    def patch_network(self):
        '''
        Return the directed graph of patch-to-patch movement.
        '''
        if self._patch_network is None:
            self._patch_network = nx.DiGraph()
            for patch in self.land_patches:
                c = np.array(patch.centroid)
                for r, p in patch.neighbors.items():
                    if p.height < self.sea_level:
                        continue
                    dist = np.linalg.norm(c - np.array(p.centroid))
                    delta_h = p.height - patch.height
                    weight = dist*np.exp(delta_h)
                    self._patch_network.add_edge(patch.name, p.name, 
                                                 weight=weight)
        return self._patch_network

    def make_road(self, start_patch, end_patch):
        '''
        Return the list of coordinates to draw a road between two patches.
        '''
        road_patches = nx.shortest_path(self.patch_network, 
                                        start_patch, end_patch, 
                                        weight='weight')
        road_coords = []
        for i in range(len(road_patches)-1):
            a = self.patches[road_patches[i]]
            b = self.patches[road_patches[i+1]]
            seg_coords = [tuple(a.centroid), tuple(b.centroid)]
            road_coords.append(seg_coords)
        return road_coords



