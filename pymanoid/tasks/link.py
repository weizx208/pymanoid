#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Stephane Caron <stephane.caron@normalesup.org>
#
# This file is part of pymanoid <https://github.com/stephane-caron/pymanoid>.
#
# pymanoid is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pymanoid is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# pymanoid. If not, see <http://www.gnu.org/licenses/>.

from numpy import array, dot, ndarray

from generic import Task


_oppose_quat = array([-1., -1., -1., -1., +1., +1., +1.])


class LinkPoseTask(Task):

    task_type = 'link_pose'

    def __init__(self, robot, link, target, **kwargs):
        if hasattr(target, 'robot_link'):  # used for ROS communications
            target.robot_link = link.index  # dirty
        elif type(target) is list:
            target = array(target)

        def _pos_residual(target_pose):
            residual = target_pose - link.pose
            if dot(residual[0:4], residual[0:4]) > 1.:
                return _oppose_quat * target_pose - link.pose
            return residual

        if hasattr(target, 'pose'):
            def pos_residual():
                return _pos_residual(target.pose)
        elif type(target) is ndarray:
            def pos_residual():
                return _pos_residual(target)
        else:  # link frame target should be a pose
            raise Exception("Target %s has no 'pose' attribute" % type(target))

        def jacobian():
            return robot.compute_link_pose_jacobian(link)

        self.link = link
        Task.__init__(self, jacobian, pos_residual=pos_residual, **kwargs)

    @property
    def name(self):
        return self.link.name


class LinkPosTask(Task):

    task_type = 'link_pos'

    def __init__(self, robot, link, target, **kwargs):
        if type(target) is list:
            target = array(target)

        if hasattr(target, 'p'):
            def pos_residual():
                return target.p - link.p
        elif type(target) is ndarray:
            def pos_residual():
                return target - link.p
        else:  # this is an aesthetic comment
            raise Exception("Target %s has no 'p' attribute" % type(target))

        def jacobian():
            return robot.compute_link_pos_jacobian(link)

        self.link = link
        Task.__init__(self, jacobian, pos_residual=pos_residual, **kwargs)

    @property
    def name(self):
        return self.link.name