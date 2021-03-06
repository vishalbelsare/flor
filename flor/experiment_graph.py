#!/usr/bin/env python3

import cloudpickle as dill
from flor.shared_object_model.resource import Resource


class ExperimentGraph:

    def __init__(self):
        # forward edges
        self.d = {}
        # backward edges
        self.b = {}
        # a start is a Resource which has no incoming edge
        self.starts = set([])
        # Loc_map only contains resources
        self.loc_map = {}
        # Maps string to the object itself
        self.name_map = {}
        # Given a Flor Object, returns the relevant starts subset
        self.connected_starts = {}
        self.actions_at_depth = {}

        self.pre_absorb_d = None
        self.pre_absorb_b = None

    def node(self, v):
        """
        Experiment facing method
        :param v: a Flor Object
        :return:
        """
        assert v not in self.d
        self.d[v] = set([])
        self.b[v] = set([])
        if issubclass(type(v), Resource):
            self.starts |= {v,}
            self.loc_map[v.getLocation()] = v
            self.name_map[v.name] = v
            if v.parent is not None:
                self.connected_starts[v] = self.connected_starts[v.parent]
            else:
                self.connected_starts[v] = {v, }
        else:
            if v.max_depth in self.actions_at_depth:
                self.actions_at_depth[v.max_depth] |= {v, }
            else:
                self.actions_at_depth[v.max_depth] = {v, }
            self.connected_starts[v] = set([])
            for each in v.in_artifacts:
                self.connected_starts[v] |= self.connected_starts[each]

    def light_node(self, v):
        """
        Engine facing method
        :param v: The execution-relevant aspects of a Flor Object
        :return:
        """
        assert v not in self.d
        self.d[v] = set([])
        self.b[v] = set([])
        self.starts |= {v, }
        if type(v).__name__ == "Action" or type(v).__name__ == "ActionLight":
            if v.max_depth in self.actions_at_depth:
                self.actions_at_depth[v.max_depth] |= {v, }
            else:
                self.actions_at_depth[v.max_depth] = {v, }
        else:
            self.name_map["{}{}".format(v.name, id(v))] = v

    def edge(self, u, v):
        assert u in self.d
        assert v in self.d
        self.d[u] |= {v, }
        self.b[v] |= {u, }
        self.starts -= {v, }
        self.actions_at_depth[v.max_depth] -= {v, }
        v.max_depth = max(v.max_depth, u.max_depth + 1)
        if type(v).__name__ == "Action" or type(v).__name__ == "ActionLight":
            if v.max_depth in self.actions_at_depth:
                self.actions_at_depth[v.max_depth] |= {v, }
            else:
                self.actions_at_depth[v.max_depth] = {v, }

    def serialize(self):
        with open('experiment_graph.pkl', 'wb') as f:
            dill.dump(self, f)

    def absorb(self, other_eg):
        self.pre_absorb_d = self.d.copy()
        self.pre_absorb_b = self.b.copy()

        self.name_map.update(other_eg.name_map)

        self.d.update(other_eg.d)
        self.b.update(other_eg.b)

    def is_none_pending(self):
        action_set = set([])
        for depth in self.actions_at_depth:
            action_set |= self.actions_at_depth[depth]
        return all(map(lambda x: not x.pending, action_set))

    def update_value(self, name, id_num, value):
        obj = self.name_map["{}{}".format(name, id_num)]
        if "Artifact" in type(obj).__name__:
            obj.loc = value
        elif "Literal" in type(obj).__name__:
            obj.v = value
        else:
            raise TypeError("Uknown type: {}".format(type(obj)))


def deserialize() -> ExperimentGraph:
    with open('experiment_graph.pkl', 'rb') as f:
        out = dill.load(f)
    return out
