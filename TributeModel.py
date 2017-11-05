'''
Implementation of the Axelrod (1995) Tribute Model [1], using an arbitrary 
network instead of a ring. Actors have wealth (which is also power) which grows
randomly. 

[1] http://www-personal.umich.edu/~axe/research/Building.pdf

Each step of the model, some actors are activated, and can choose to demand
tribute of their neighbors; the recipients, then, can choose to pay tribute or 
go to war. When actors pay or receive tribute, their commitment to one another 
increases. When they fight on opposite sides of a war, their commitment 
decreases.

Actors go to war in Coalitions. A coalition is composed of all actors who are 
between the two primary actors (i.e. the one demanding tribute and the target
of the demand), and who have a higher commitment to one side than the other. An
actor can only demand tribute from another if they can assemble a coalition 
which reaches that actor.


'''

import random
from itertools import permutations
import networkx as nx

class Actor:
    '''
    One simulated political actor
    '''

    def __init__(self, model, name, wealth=None):
        '''
        Create a new actor

        Args:
            model: parent model object
            name: An arbitrary unique label
            wealth: Initial wealth; if None, it will be random.

        '''
        self.name = name
        self.model = model
        if wealth is None:
            self.wealth = random.uniform(300, 500)
        else:
            self.wealth = wealth
        self.commitment = {a: 0 for a in self.model.network
                          if a != self.name}
        self.commitment[self.name] = 1
        self.log = []
        self.wealth_history = []
    
    def activate(self):
        '''
        The actor checks other actors for vulnerability, and demands tribute.
        '''
        vulnerabilities = {a: self.assess_vulnerability(a) 
                          for a in self.model.agents.values()
                          if self.check_target(a) and a is not self
                          and a.wealth > 0}
        if len(vulnerabilities) == 0: return
        target = max(vulnerabilities, key=lambda x: vulnerabilities[x])
        if vulnerabilities[target] >= 0:
            if self.model.verbose:
                print("{} threatens {}".format(self.name, target.name))
            target.receive_tribute_demand(self)

    def record_history(self):
        self.wealth_history.append(self.wealth)
    
    def check_target(self, target):
        '''Is there a path to the target?
        '''
        for path in nx.all_simple_paths(self.model.network, self.name, target.name):
            if len(path) == 2:
                return True
            path = path[1:-1]
            for node in path:
                a = self.model.agents[node]
                if not a.check_support(self, target):
                    break
            else:
                return True
        return False
    
    def check_support(self, source, target):
        '''
        Return True if supports source more than target.
        '''
        return self.commitment[source.name] > self.commitment[target.name]
    
    def assess_vulnerability(self, target):
        '''Heuristic for estimating target's vulnerability.
        '''
        if self.wealth == 0:
            return 0
        return (self.wealth - target.wealth)/self.wealth

    def receive_tribute_demand(self, attacker):
        '''Decide whether to pay tribute.
        '''
        
        attack_coalition = Coalition(self.model, attacker, self)
        defender_coalition = Coalition(self.model, self, attacker)
        tribute = min(self.wealth, self.model.tribute)
        damage = (self.model.damage * attack_coalition.total_strength * 
                  (self.wealth / defender_coalition.total_strength))
            
        if min(damage, self.wealth) < tribute:
            # Pay tribute
            if self.model.verbose:
                print("{} paying tribute".format(self.name))
            attacker.wealth += tribute
            self.wealth -= tribute
            
            attacker.change_commitment(self, 0.1)
            self.change_commitment(attacker, 0.1)

            attacker.add_event("Receive tribute", self)
            self.add_event("Pay tribute", attacker)
        else:
            self.model.war(attack_coalition, defender_coalition)
            
    def change_commitment(self, agent, increment):
        if agent is self: 
            return
        self.commitment[agent.name] += increment
        self.commitment[agent.name] = max(0, 
                                         min(1, self.commitment[agent.name]))

    def add_event(self, event, other):
        event = (self.model.year, event, other.name)
        self.log.append(event)

class Coalition:
    '''
    Temporary class to hold the actors (potentially) fighting together in a war
    '''

    def __init__(self, model, leader, target):
        '''
        Create a new coalition.

        Args:
            model: parent model object
            leader: The leader of this coalition.
            target: The leader of the other side
        '''

        self.leader = leader
        self.target = target
        self.model = model
        
        self.members = [self.leader]
        #self.total_strength = self.leader.wealth
        self.total_strength = self.leader.wealth
        self.member_contributions = {self.leader.name: self.leader.wealth}
        for agent in self.model.agents.values():
            if self.check_member(agent) and agent not in [self.leader, self.target]:
                self.members.append(agent)
                contribution = agent.wealth * agent.commitment[self.leader.name]
                self.total_strength += contribution
                self.member_contributions[agent.name] = contribution
    
    def check_member(self, agent):
        '''
        Check whether an agent can join the coalition
        '''
        if not agent.check_support(self.leader, self.target):
            return False
        for path in nx.all_simple_paths(self.model.network, 
                                        agent.name, self.target.name):
            if len(path) == 2:
                return True
            path = path[1:-1]
            for node in path:
                if not self.model.agents[node].check_support(self.leader, 
                                                             self.target):
                    break
            else:
                return True
        return False
    
    def inflict_damage(self, enemy):
        '''
        Inflict damage on all members based on the strength of the enemy coalition
        '''
        if self.total_strength == 0: 
            return
        total_damage = self.model.damage * enemy.total_strength
        for actor in self.members:
            #damage =  total_damage * (actor.commitment[self.leader.name]*actor.wealth 
            #                          / self.total_strength)
            damage = total_damage * (self.member_contributions[actor.name] 
                                    / self.total_strength)
            damage = min(damage, actor.wealth)
            actor.wealth -= damage
    
    def increase_commitment(self):
        for a1, a2 in permutations(self.members, 2):
            a1.change_commitment(a2, 0.1)

    def log_war(self):
        self.leader.add_event("Led war against", self.target)
        for a in self.members:
            if a == self.leader: continue
            a.add_event("Joined war against", self.target)

    def get_dict(self):
        '''
        Return a dictionary representation of the war.
        '''
        return {"leader": self.leader.name,
                "target": self.target.name,
                "members": self.member_contributions}


    def __str__(self):
        text = "Leader: {};".format(self.leader.name)
        if len(self.members) > 1:
            text += " Members: {};".format([m.name for m in self.members 
                                          if m != self.leader])
        text += " Target: {}".format(self.target.name)
        return text


class Model:
    '''
    A single run of the entire Tribute Model.
    '''

    def __init__(self, network, tribute=250, damage=0.25, verbose=False):
        '''
        Create a new model instantiation.

        Args:
            network: The initial network of actors
            tribute: The size of the tribute demanded
            damage: What fraction of enemy wealth is dealt as damage in war
            verbose: Whether to print all actions as they happen.
        '''
        
        self.tribute = tribute
        self.damage = damage
        self.network = network
        self.verbose = verbose
        self.activations_per_year = 3
        self.year = 0
        self.make_agents()
        self.wars = []

    def make_agents(self):

        self.agents = {}
        for node in self.network:
            wealth = None
            if "wealth" in self.network.node[node]:
                wealth = self.network.node[node]["wealth"]
            a = Actor(self, node, wealth)
            self.agents[node] = a
        self.agent_names = [a.name for a in self.agents.values()]

    def step(self):
        for _ in range(self.activations_per_year):
            a = self.agents[random.choice(self.agent_names)]
            a.activate()

        for a in self.agents.values():
            a.record_history()
        # Harvest season
        for a in self.agents.values():
            a.wealth += 20
        self.year += 1

    
    def war(self, attackers, defenders):
        '''
        Fight a war between the attackers and defenders coalitions
        '''
        attackers.inflict_damage(defenders)
        defenders.inflict_damage(attackers)
        attackers.increase_commitment()
        defenders.increase_commitment()
        for a in attackers.members:
            for d in defenders.members:
                a.change_commitment(d, -0.1)
                d.change_commitment(a, -0.1)
        attackers.log_war()
        defenders.log_war()
        war_log = {"year": self.year,
                    "attackers": attackers.get_dict(),
                    "defenders": defenders.get_dict()}
        self.wars.append(war_log)
        if self.verbose:
            print(attackers)
            print(defenders)