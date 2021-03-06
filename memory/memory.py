# coding: utf-8
'''
'''

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

    def as_dict(self):
        '''Get the MemoryTimestamp as a dict.
        '''
        return {
            'created': self.created,
            'last_updated': self.last_updated,
            'last_accessed': self.last_accessed,
        }


class MemoryPattern:
    '''A memory pattern is represented as a collection of interconnected nodes;
    each node represents a key feature of the memory and has a unique level of
    activation.
    '''
    def __init__(self, m_id, keywords, description=None, content=None, valence=None, weight=1.0, at=None):
        '''Create a new memory; at minimum, a memory must consist of an ID
        unique to a given agent, and a list of keywords relating to the memory.
        '''
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

    def as_dict(self):
        '''Get the MemoryPattern as a dict.
        '''
        return {
            'id': self.m_id,
            'keywords': list(self.keywords),
            'description': self.description,
            'content': self.content,
            'valence': self.valence,
            'weight': self.weight,
            'timestamp': self.timestamp.as_dict(),
        }


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

    def as_dict(self):
        '''Get the MemoryNode as a dict.
        '''
        return {
            'keyword': self.keyword,
            'links': self.links,
            'activation': self.activation,
        }

    def activate(self, factor, strength=1.0):
        '''Activate this node.

        When a given node is activated by either the memory manager or
        another node, if the incoming activation is greater than the node's
        current activation the node’s activation increases as a weighted average
        of the incoming activation and its current activation value.
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
    '''Collection of MemoryPatterns and associated MemoryNodes, representing
    an agent's memories and their features at one level of memory hierarchy.
    '''
    def __init__(self, name):
        self.name = name
        self._nodes = dict()
        self._memories = dict()

    def __len__(self):
        '''Get the number of nodes in the pool.

        Returns:
            int
        '''
        return len(self._nodes)

    def __contains__(self, keyword):
        '''Check if the MemoryPool contains a node by keyword.

        Returns:
            bool
        '''
        return keyword in self._nodes

    def _add_node(self, keyword):
        '''Add a node to the internal node store.

        If the passed `keyword` does not exist within the pool, this creates a
        new MemoryNode and adds it to the `_nodes` dict.

        Args:
            keyword (str)
        '''
        if keyword not in self._nodes:
            self._nodes[keyword] = MemoryNode(keyword)

    def activate(self, keyword, factor=1.0):
        '''Activate a MemoryNode by keyword.

        Following activation, a node passes an outgoing signal to all linked
        nodes; this outgoing activation is a fraction of its own new activation
        value.
        Nodes do not 'backtalk' and spread activation back to the
        nodes that activated them, nor can a node's activation value be
        decreased by an incoming activation.

        Args:
            keyword (str): Keyword for node to activate.
            factor (float, optional)

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

    def as_dict(self):
        '''Get the MemoryPool as a dict.
        '''
        return {
            'name': self.name,
            'nodes': [node.as_dict() for node in self._nodes.values()],
            'memories': list(self._memories)
        }

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

        Args:
            memory (MemoryPattern)
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

        Args:
            keyword (str)

        Returns:
            (float, MemoryPattern)
        '''
        candidates = None
        for pool in (self.immediate, self.shortterm, self.longterm):
            if keyword in pool:
                candidates = pool.activate(keyword)
                break
        if not candidates:
            return (None, None)
        results = [(memory.score(candidates), memory) for memory in self._memories.values()]
        return max(results, key=lambda x: x[0])

    def get(self, memory_id):
        '''Get a memory by id.
        '''
        return self._memories.get(memory_id)

    def pretty_print(self):
        '''Pretty-print the contents of each pool.
        '''
        for pool in (self.immediate, self.shortterm, self.longterm):
            pool.pretty_print()

    def as_dict(self):
        '''Get the Memory as a dict.
        '''
        return {
            'memories': [mem.as_dict() for mem in self._memories.values()],
            'immediate': self.immediate.as_dict(),
            'shortterm': self.shortterm.as_dict(),
            'longterm': self.longterm.as_dict(),
        }


class Agent:
    '''Agent model, comprising memory, personality traits, mood, and social
    ties.
    '''
    def __init__(self):
        self.memory = Memory()
        self.personality = None
        self.mood = None
        self.ties = None


def main():
    agt = Agent()
    agt.memory.create_memory(0, 'fish lake cottage vacation'.split(), description='fishing at the lake by the cottage on vacation')
    agt.memory.create_memory(1, 'vacation dad scotland'.split(), description='going on vacation with Dad to Scotland')
    agt.memory.create_memory(2, 'vacation dad ireland'.split(), description='going on vacation with Dad to Ireland')
    agt.memory.create_memory(3, 'fish dinner london'.split(), description='eating a fish dinner in london')

    for trigger in ('vacation', 'fish', 'london'):
        score, mem = agt.memory.match(trigger)
        print(f'trigger [{trigger.upper()}] {score:.2f} - {mem}')
    print()
    agt.memory.pretty_print()
    # print(json.dumps(a.memory.as_dict(), indent=2))


if __name__ == '__main__':
    main()
