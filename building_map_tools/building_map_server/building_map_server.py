import errno
import math
import os
import sys
import yaml

from numpy import inf

import rclpy
from rclpy.qos import QoSProfile
from rclpy.qos import QoSHistoryPolicy as History
from rclpy.qos import QoSDurabilityPolicy as Durability
from rclpy.qos import QoSReliabilityPolicy as Reliability
from rclpy.node import Node

from building_map_msgs.srv import GetBuildingMap
from building_map_msgs.msg import BuildingMap
from building_map_msgs.msg import Level
from building_map_msgs.msg import Graph
from building_map_msgs.msg import GraphNode
from building_map_msgs.msg import GraphEdge
from building_map_msgs.msg import Place
from building_map_msgs.msg import AffineImage
from building_map_msgs.msg import Door
from building_map_msgs.msg import Lift

from building_map.building import Building


class BuildingMapServer(Node):
    def __init__(self, map_path):
        super().__init__('building_map_server')

        self.get_logger().info('loading map path: {}'.format(map_path))

        if not os.path.isfile(map_path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), map_path)
        self.map_dir = os.path.dirname(map_path)  # for calculating image paths

        with open(map_path, 'r') as f:
            self.building = Building(yaml.safe_load(f))

        self.map_msg = self.building_map_msg(self.building)

        self.get_building_map_srv = self.create_service(
            GetBuildingMap, 'get_building_map', self.get_building_map)

        qos = QoSProfile(
            history=History.RMW_QOS_POLICY_HISTORY_KEEP_LAST,
            depth=1,
            reliability=Reliability.RMW_QOS_POLICY_RELIABILITY_RELIABLE,
            durability=Durability.RMW_QOS_POLICY_DURABILITY_TRANSIENT_LOCAL)

        self.building_map_pub = self.create_publisher(
            BuildingMap, 'map', qos_profile=qos)

        self.get_logger().info('publishing map...')
        self.building_map_pub.publish(self.map_msg)

        self.get_logger().info(
            'ready to serve map: "{}"  Ctrl+C to exit...'.format(
                self.map_msg.name))

    def building_map_msg(self, building):
        msg = BuildingMap()
        msg.name = building.name
        for _, level_data in building.levels.items():
            msg.levels.append(self.level_msg(level_data))
        for _, lift_data in building.lifts.items():
            msg.lifts.append(self.lift_msg(lift_data))
        return msg

    def level_msg(self, level):
        msg = Level()
        msg.name = level.name
        msg.elevation = level.elevation
        if level.drawing_name:
            image = AffineImage()
            image_filename = level.drawing_name
            image.encoding = image_filename.split('.')[-1]
            image.scale = level.transform.scale
            image.x_offset = level.transform.translation[0]
            image.y_offset = level.transform.translation[1]
            image.yaw = level.transform.rotation

            image_path = os.path.join(self.map_dir, image_filename)

            print('opening: {}'.format(image_path))
            with open(image_path, 'rb') as image_file:
                image.data = image_file.read()
            print('read {} byte image: {}'.format(
                len(image.data), image_filename))
            msg.images.append(image)

        if (len(level.doors)):
            for door in level.doors:
                door_msg = Door()
                door_msg.door_name = door.params['name'].value
                door_msg.v1_x = level.vertices[door.start_idx].x
                door_msg.v1_y = level.vertices[door.start_idx].y
                door_msg.v2_x = level.vertices[door.end_idx].x
                door_msg.v2_y = level.vertices[door.end_idx].y
                door_msg.motion_range = float(
                    door.params['motion_degrees'].value)
                door_msg.motion_direction = door.params[
                    'motion_direction'].value
                door_type = door.params['type'].value
                if door_type == 'sliding':
                    door_msg.door_type = door_msg.DOOR_TYPE_SINGLE_SLIDING
                elif door_type == 'hinged':
                    door_msg.door_type = door_msg.DOOR_TYPE_SINGLE_SWING
                elif door_type == 'double_sliding':
                    door_msg.door_type = door_msg.DOOR_TYPE_DOUBLE_SLIDING
                elif door_type == 'double_hinged':
                    door_msg.door_type = door_msg.DOOR_TYPE_DOUBLE_SWING
                else:
                    door_msg.door_type = door_msg.DOOR_TYPE_UNDEFINED
                msg.doors.append(door_msg)

        # for now, nav graphs are just single-digit numbers
        for i in range(0, 9):
            g = level.generate_nav_graph(i, always_unidirectional=False)
            if not g['lanes']:
                continue  # empty graph :(
            graph_msg = Graph()
            graph_msg.name = str(i)  # todo: someday, string names...
            for v in g['vertices']:
                gn = GraphNode()
                gn.x = v[0]
                gn.y = v[1]
                gn.name = v[2]['name']
                graph_msg.vertices.append(gn)
            for l in g['lanes']:
                ge = GraphEdge()
                ge.v1_idx = l[0]
                ge.v2_idx = l[1]
                if l[2]['is_bidirectional']:
                    ge.edge_type = GraphEdge.EDGE_TYPE_BIDIRECTIONAL
                else:
                    ge.edge_type = GraphEdge.EDGE_TYPE_UNIDIRECTIONAL
                graph_msg.edges.append(ge)
            msg.nav_graphs.append(graph_msg)
        return msg
    
    def lift_msg(self, lift):
        msg = Lift()
        msg.name = lift.name
        msg.levels = lift.level_names
        msg.ref_x = lift.x
        msg.ref_y = lift.y
        msg.ref_yaw = lift.yaw
        msg.width = lift.width
        msg.depth = lift.depth
        return msg

    def get_building_map(self, request, response):
        self.get_logger().info('get_building_map()')
        # todo: only include images/graphs if they are requested?
        response.building_map = self.map_msg
        return response


def main():
    if len(sys.argv) > 1:
        map_path = sys.argv[1]
    elif 'RMF_MAP_PATH' in os.environ:
        map_path = os.environ['RMF_MAP_PATH']
    else:
        print('map path must be provided in command line or RMF_MAP_PATH env')
        sys.exit(1)
        raise ValueError('Map path not provided')

    rclpy.init()
    n = BuildingMapServer(map_path)
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    sys.exit(main())
