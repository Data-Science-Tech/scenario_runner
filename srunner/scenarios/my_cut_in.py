# scenario_runner/srunner/scenarios/my_cut_in.py
import py_trees
import carla

from srunner.scenarios.basic_scenario import BasicScenario
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from srunner.scenariomanager.scenarioatomics.atomic_trigger_conditions import InTriggerDistanceToLocation
from srunner.scenariomanager.scenarioatomics.atomic_behaviors import (
    ActorTransformSetter, WaypointFollower, LaneChange, Idle
)

class MyCutIn(BasicScenario):
    """
    config.trigger_points[0]：触发点
    config.other_actors[0]：切入车 spawn 位姿
    config.other_parameters：自定义参数（target_speed / cut_in_distance / target_lane）
    """

    def __init__(self, world, ego_vehicles, config, timeout=60):
        self._world = world
        self._map = CarlaDataProvider.get_map()

        # 读参数（来自 routes.xml 的 <target_speed value="..."/> 等）
        p = config.other_parameters
        self._target_speed = float(p.get("target_speed", {}).get("value", 10.0))
        self._trigger_location = config.trigger_points[0].location

        super().__init__("MyCutIn", ego_vehicles, config, world, debug_mode=False, criteria_enable=True)

    def _initialize_actors(self, config):
        """
        把 routes.xml 里的 other_actor 刷出来
        BasicScenario 通常会提供 helper（如 setup_vehicle），你也可以直接用 CarlaDataProvider.request_new_actor
        """
        for actor_cfg in config.other_actors:
            bp = actor_cfg.model  # 例如 vehicle.tesla.model3
            transform = actor_cfg.transform
            npc = CarlaDataProvider.request_new_actor(bp, transform, rolename='scenario')
            self.other_actors.append(npc)

    def _create_behavior(self):
        ego = self.ego_vehicles[0]
        npc = self.other_actors[0]

        root = py_trees.composites.Sequence(name="MyCutInSequence")

        # 1) 等待触发：ego 接近 trigger_point（你也可以换成 InTriggerDistanceToVehicle）
        root.add_child(InTriggerDistanceToLocation(ego, self._trigger_location, 15.0))

        # 2) 让 NPC 开始沿路走/保持速度（WaypointFollower 会用简单跟随逻辑）
        root.add_child(WaypointFollower(npc, self._target_speed))

        # 3) 切入动作：LaneChange（方向/目标车道可由参数决定）
        # 注意：LaneChange 的参数形式以当前 SR 版本为准，可参考 change_lane.py 的用法
        root.add_child(LaneChange(npc, direction='right', distance_same_lane=5, distance_other_lane=15))

        # 4) 切入后继续走一段
        root.add_child(Idle(3.0))

        return root

    def _create_test_criteria(self):
        # 可选：给这个子场景加额外评价准则（碰撞等通常 route 已经有）
        return []

