"""
Copyright (C) 2017 Open Source Robotics Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import math
from shapely.geometry import LineString
from geometry.point import Point
from geometry.bounding_box import BoundingBox

from city_model import CityModel
from road_simple_node import RoadSimpleNode
from road_intersection_node import RoadIntersectionNode
from lane import Lane
from road_node import RoadNode


class Road(CityModel):
    def __init__(self, name=None):
        super(Road, self).__init__(name)
        self._nodes = []
        self._point_to_node = {}
        self._lanes = []

    @classmethod
    def from_nodes(cls, array_of_nodes):
        """
        Please use the `from_control_points` class method if possible. This method
        will be deprecated in the future.
        """
        road = cls()
        for node in array_of_nodes:
            road._add_node(node)
        return road

    @classmethod
    def from_control_points(cls, array_of_points):
        road = cls()
        for point in array_of_points:
            road.add_control_point(point)
        return road

    # Geometry

    def width(self):
        external_offsets = map(lambda lane: lane.external_offset(), self.lanes())
        return abs(min(external_offsets)) + abs(max(external_offsets))

    def bounding_box(self):
        node_bounding_boxes = self._node_bounding_boxes()
        return BoundingBox.from_boxes(node_bounding_boxes)

    # Control points management

    def control_points(self):
        return map(lambda node: node.center, self._nodes)

    def control_points_as_line_string(self):
        coords = map(lambda node: node.center.to_tuple(), self._nodes)
        return LineString(coords)

    def add_control_point(self, point):
        node = RoadSimpleNode(point)
        self._add_node(node)
        self._point_to_node[point] = node

    def add_control_points(self, points):
        for point in points:
            self.add_control_point(point)

    def control_points_count(self):
        return len(self._nodes)

    def includes_control_point(self, point):
        # Attempt a constant search in the points dictionary. If that fails
        # do the linear search in the nodes collection.
        return (point in self._point_to_node) or \
            any(node.center.almost_equal_to(point, 5) for node in self._nodes)

    def control_points_distances(self):
        points = self.control_points()
        if len(points) == 1:
            return [0.0]
        point_pairs = zip(points, points[1:])
        return map(lambda point_pair: point_pair[0].distance_to(point_pair[1]), point_pairs)

    def sum_control_points_distances(self, initial=0, final=None):
        distances = self.control_points_distances()
        if final is None:
            return math.fsum(distances[initial:])
        return math.fsum(distances[initial:final])

    # Lane management

    def add_lane(self, offset, width=4, reversed=False):
        self._lanes.append(Lane(self, width, offset, reversed))

    def lane_count(self):
        return len(self._lanes)

    def lanes(self):
        return self._lanes

    def lane_at(self, index):
        return self._lanes[index]

    # Nodes management

    def reverse(self):
        self._nodes.reverse()

    def nodes(self):
        return self._nodes

    def node_at(self, index):
        return self._nodes[index]

    def node_count(self):
        return len(self._nodes)

    def first_node(self):
        return self._nodes[0]

    def last_node(self):
        return self._nodes[-1]

    def is_first_node(self, node):
        return self.first_node() is node

    def is_last_node(self, node):
        return self.last_node() is node

    def replace_node_at(self, point, new_node):
        index = self._index_of_node_at(point)
        old_node = self._nodes[index]
        self._nodes[index] = new_node
        new_node.added_to(self)
        old_node.removed_from(self)

    def trim_redundant_nodes(self, angle=0):
        previous_node = self.first_node()
        trimmed_nodes = [previous_node]
        for index in range(1, self.node_count() - 1):
            current_node = self.node_at(index)
            following_node = self.node_at(index + 1)
            previous_vector = current_node.center - previous_node.center
            following_vector = following_node.center - current_node.center
            if current_node.is_intersection() or \
               (abs(previous_vector.angle(following_vector)) > angle):
                trimmed_nodes.append(current_node)
                previous_node = current_node
        trimmed_nodes.append(self.last_node())
        self._nodes = trimmed_nodes

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
            self.width() == other.width() and \
            self._nodes == other._nodes

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.width(), tuple(self._nodes)))

    def __repr__(self):
        return "%s: " % self.__class__.__name__ + \
            reduce(lambda acc, node: acc + "%s," % str(node), self._nodes, '')

    def _node_bounding_boxes(self):
        return map(lambda node: node.bounding_box(self.width()), self._nodes)

    def _index_of_node_at(self, point):
        return next((index for index, node in enumerate(self._nodes) if node.center == point), None)

    def _add_node(self, node):
        self._nodes.append(node)
        node.added_to(self)
