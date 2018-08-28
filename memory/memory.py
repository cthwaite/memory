# coding: utf-8

import itertools
import json


class MemoryTimestamp:
    '''Identifies when a memory pattern was first created, last accessed, and
    last updated.
    '''
    __slots__ = ('created', 'last_updated', 'last_accessed') 
    def __init__(self, time):
        self.created = time
        self.last_updated = time
        self.last_accessed = time


class MemoryPattern:
    '''[A] memory pattern is represented as a collection of interconnected nodes;
    each node represents a key feature of the memory and has a unique level of
    activation.
    '''
    def __init__(self, m_id, keywords, description=None, content=None, valence=None, weight=1.0, at=None):
        self.m_id = m_id
        self.keywords = set(keywords)
        self.description = description
        self.content = content
        self.valence = valence
        self.weight = weight
        self.timestamp = MemoryTimestamp(at)

    def __repr__(self):
        return f'<MemoryPattern {self.m_id} - {self.description}>'
    
    def __hash__(self):
        '''A MemoryPattern is hashed on its id.
        '''
        return hash(self.m_id)
    
    def __eq__(self, other):
        '''A MemoryPattern is equal to another MemoryPattern if they share the
        same id.

        Args:
            other (MemoryPattern)
        '''
        if isinstance(other, MemoryPattern):
            return self.m_id == other.m_id
        raise NotImplementedError

    def score(self, nodes):
        '''Get the score for this MemoryPattern given a set of nodes.

        Args:
            nodes (iterable)
        '''
        return sum(node.activation for node in nodes if node.keyword in self.keywords)


class MemoryNode:
    '''Key term within a MemoryPattern.
    '''
    def __init__(self, keyword, links=None):
        self.keyword = keyword
        self.links = links or {}
        self.activation = 0.0
    
    def __repr__(self):
        return f"<MemoryNode '{self.keyword}' ({self.activation:.2f})>"

    def __hash__(self):
        '''The has of a MemoryNode is the has of its keyword.
        '''
        return hash(self.keyword)
    
    def __eq__(self, other):
        '''A MemoryNode is equal to another MemoryNode if they share the same
        keyword.

        Args:
            other (MemoryNode)
        '''
        if isinstance(other, MemoryNode):
            return self.keyword == other.keyword
        raise NotImplementedError

    def activate(self, factor, strength=1.0):
        '''
        '''
        if factor > self.activation:
            self.activation += ((factor * strength) + self.activation) / 2

    def link(self, other):
        '''As the control system parses a pattern, if a connection between two
        nodes already exists, its strength is increased.
        '''
        if other in self.links:
            self.links[other] += 1.0
        else:
            self.links[other] = 1.0


class MemoryPool:
    def __init__(self, name):
        self.name = name
        self._nodes = dict()
        self._memories = dict()

    def __len__(self):
        '''Get the number of nodes in the pool.
        '''
        return len(self._nodes)

    def __contains__(self, keyword):
        return keyword in self._nodes

    def _add_node(self, keyword):
        '''
        '''
        if keyword not in self._nodes:
            self._nodes[keyword] = MemoryNode(keyword)

    def activate(self, keyword, factor=1.0):
        '''When a given node is activated by either the memory manager or
        another node, if the incoming activation is greater than the node's
        current activation the node’s activation increases as a weighted average
        of the incoming activation and its current activation value.
        Following this increase in activation, the node then passes an outgoing
        activation to all of the nodes it is connected to; this outgoing
        activation is a fraction of its own new activation value.
        Importantly, nodes do not 'backtalk' and spread activation back to the
        nodes that activated them, nor can a node's activation value be
        decreased by an incoming activation. 

        Args:
            keyword (str)
            factor (float)

        Returns:
            set: Set of nodes to compare.
        '''
        candidate = self._nodes[keyword]
        candidate.activate(factor)
        check = set()
        for link, strength in candidate.links.items():
            linked = self._nodes[link]
            linked.activate(factor / 3, strength)
            check.add(linked)
        check.add(candidate)
        return check

    def add(self, memory):
        '''Add a memory to the pool.
        
        When the control system receives a new memory pattern the keywords
        from the pattern are first parsed into the immediate memory pool.
        If one of the pattern’s keywords is not already represented as a node
        in the immediate memory pool network, a node for that keyword is
        created (duplicates are not allowed). Each node is connected
        unidirectionally to every other node in its memory pattern, so any
        two connected nodes are connected bidirectionally. 
        '''
        if memory.m_id in self._memories:
            raise ValueError('Memory %r already exists in pool %s' % memory, self.name)
        for keyword in memory.keywords:
            self._add_node(keyword)
        for (node, sibling) in itertools.combinations(memory.keywords, 2):
            self._nodes[node].link(sibling)
            self._nodes[sibling].link(node)
        self._memories[memory.m_id] = memory

    def is_empty(self):
        '''Check if the MemoryPool is empty; an empty pool has no nodes.

        Returns:
            bool
        '''
        return not len(self._nodes)

    def iternodes(self):
        '''Iterate over nodes in the MemoryPool.

        Yields:
            MemoryNode
        '''
        for node in self._nodes:
            yield node

    def pretty_print(self):
        '''Pretty-print the contents of the pool.
        '''
        print(f'{self.name: ^15}')
        print('-' * 15)

        if self.is_empty():
            print('( empty )', end='\n\n')
            return
        for node in self._nodes.values():
            print(f'{node.keyword} [{node.activation:.2f}]')
            for link, strength in node.links.items():
                print(f'├─({strength:.2f})─> {link}')
            print()

    def remove(self, memory):
        '''Remove a memory from the pool.

        Nodes within each pool are persistent, and remain even after the memory
        that was used to form them has been moved to another pool.
        '''
        del self._memories[memory.m_id]
        for node in memory.keywords:
            del self._nodes[node]


class Memory:
    '''Complete memory model, comprising three hierarchically arranged memory
    pools: immediate memory, short term memory, and long term memory.
    '''
    def __init__(self):
        self.immediate = MemoryPool('immediate')
        self.shortterm = MemoryPool('shortterm')
        self.longterm = MemoryPool('longterm')
        self._memories = dict()

    def create_memory(self, *args, **kwargs):
        '''Create a new memory, adding it to the `immediate` pool.
        '''
        new_mem = MemoryPattern(*args, **kwargs)
        self.immediate.add(new_mem)
        self._memories[new_mem.m_id] = new_mem

    def match(self, keyword):
        '''Find a memory matching the given keyword.
        '''
        candidates = None
        for pool in (self.immediate, self.shortterm, self.longterm):
            if keyword in pool:
                candidates = pool.activate(keyword)
                break
        if not candidates:
            return
        results = [(memory.score(candidates), memory) for memory in self._memories.values()]
        return max(results, key=lambda x: x[0])
    
    def get(self, memory_id):
        '''Get a memory by id.
        '''
        return self._memories.get(memory_id)

    def pretty_print(self):
        for pool in (self.immediate, self.shortterm, self.longterm):
            pool.pretty_print()


class Agent:
    def __init__(self):
        self.memory = Memory()
        self.personality = None
        self.mood = None
        self.ties = None


def main():
    a = Agent()
    a.memory.create_memory(0, 'fish lake cottage vacation'.split(), description='fishing at the lake by the cottage on vacation')
    a.memory.create_memory(1, 'vacation dad scotland'.split(), description='going on vacation with Dad to Scotland')
    a.memory.create_memory(2, 'vacation dad ireland'.split(), description='going on vacation with Dad to Ireland')
    a.memory.create_memory(3, 'fish dinner london'.split(), description='eating a fish dinner in london')

    for trigger in ('vacation', 'fish', 'london'):
        score, mem = a.memory.match(trigger)
        print(f'trigger [{trigger.upper()}] {score:.2f} - {mem}')
    print()
    a.memory.pretty_print()


if __name__ == '__main__':
    main()