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

from numpy import array, dot, zeros, ndarray
from task import Task


class COMTask(Task):

    task_type = 'com'

    def __init__(self, robot, target, **kwargs):
        """
        Add a COM tracking task.

        INPUT:

        - ``robot`` -- a CentroidalRobot object
        - ``target`` -- coordinates or any Body object with a 'pos' attribute
        """
        self.robot = robot
        jacobian = self.robot.compute_com_jacobian
        pos_residual = self.compute_pos_residual(target)
        Task.__init__(self, jacobian, pos_residual=pos_residual, **kwargs)

    def compute_pos_residual(self, target):
        if type(target) is list:
            target = array(target)
        if type(target) is ndarray:
            def pos_residual():
                return target - self.robot.com
        elif hasattr(target, 'p'):
            def pos_residual():
                return target.p - self.robot.com
        else:  # COM target should be a position
            raise Exception("Target %s has no 'p' attribute" % type(target))
        return pos_residual

    def update_target(self, target):
        self.pos_residual = self.compute_pos_residual(target)


class ConstantCAMTask(Task):

    task_type = 'constantcam'

    def __init__(self, robot, **kwargs):
        """
        Try to keep the centroidal angular momentum constant.

        INPUT:

        - ``robot`` -- a CentroidalRobot object

        .. NOTE::

            The way this task is implemented may be surprising. Basically,
            keeping a constant CAM means d/dt(CAM) == 0, i.e.,

                d/dt (J_cam * qd) == 0
                J_cam * qdd + qd * H_cam * qd == 0

            Because the IK works at the velocity level, we approximate qdd by
            finite difference from the previous velocity (``qd`` argument to the
            residual function):

                J_cam * (qd_next - qd) / dt + qd * H_cam * qd == 0

            Finally, the task in qd_next (output velocity) is:

                J_cam * qd_next == J_cam * qd - dt * qd * H_cam * qd

            Hence, there are two occurrences of J_cam: one in the task residual,
            and the second in the task jacobian.

        """
        def vel_residual(dt):
            qd = robot.qd
            J_cam = robot.compute_cam_jacobian()
            H_cam = robot.compute_cam_hessian()  # computation intensive :(
            return dot(J_cam, qd) - dt * dot(qd, dot(H_cam, qd))

        jacobian = robot.compute_cam_jacobian
        Task.__init__(self, jacobian, vel_residual=vel_residual, **kwargs)


class MinCAMTask(Task):

    task_type = 'mincam'

    def __init__(self, robot, **kwargs):
        """
        Minimize the centroidal angular momentum.

        INPUT:

        - ``robot`` -- a CentroidalRobot object
        """
        def vel_residual(dt):
            return zeros((3,))

        jacobian = robot.compute_cam_jacobian
        Task.__init__(self, jacobian, vel_residual=vel_residual, **kwargs)