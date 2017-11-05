'''
Nomads Model
=================

Create nomadic tribes who wander around a generated world.
'''

import random
from collections import defaultdict
import networkx as nx

def weighted_random(choices):
    total = sum(w for c, w in choices.items())
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices.items():
        if upto + w >= r:
            return c
        upto += w
    assert False, "Shouldn't get here"

class Nomad:
    '''
    A nomadic tribe.
    '''

    def __init__(self, model, name, patch, starting_size=1):
        self.model = model
        self.name = name
        self.patch = patch
        self.size = starting_size
    
    def evaluate_patch(self, patch):
        water = 1000 * self.get_water(patch)
        slope = min(1 / patch.slope, 5)
        elevation = 10 * (1 - patch.height)
        return slope + water + elevation

    @staticmethod
    def get_water(patch):
        return sum([v.flux for v in patch.vertices])

    def move(self):
        if random.random() > 1 / self.size:
            return
        possible_moves = [p for p in self.patch.neighbors.values()
                         if p.height > self.model.world.sea_level]
        possible_moves += [self.patch]
        move_weights = {patch: self.evaluate_patch(patch) 
                        for patch in possible_moves}
        next_patch = weighted_random(move_weights)
        self.patch = next_patch

class NomadModel:
    def __init__(self, world, num_tribes):
        self.world = world
    
        self.nomads = []
        for i in range(num_tribes):
            starting_patch = random.choice(self.world.land_patches)
            tribe = Nomad(self, i, starting_patch)
            self.nomads.append(tribe)

    def one_year(self):
        for tribe in self.nomads:
            tribe.move()

        # If two tribes end up on the same patch, they join together
        nomads_per_patch = defaultdict(list)
        for tribe in self.nomads:
            nomads_per_patch[tribe.patch].append(tribe)

        self.nomads = []
        for patch, patch_tribes in nomads_per_patch.items():
            patch_tribes[0].size = sum([t.size for t in patch_tribes])
            self.nomads.append(patch_tribes[0])

        



