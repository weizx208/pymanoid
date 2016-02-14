#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Stephane Caron <stephane.caron@normalesup.org>
#
# This file is part of pymanoid.
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


import uuid

from body import Box
from numpy import array, cross, dot, hstack, zeros
from scipy.linalg import block_diag
from toolbox import cvxopt_solve_qp


class RectangularContact(Box):

    def __init__(self, env, X, Y, pos, rpy, friction, Z=0.01, color='r',
                 name=None, pose=None, visible=False):
        """
        Create a new rectangular contact

        X -- half-length of the contact surface
        Y -- half-width of the contact surface
        pos -- initial position of the contact frame w.r.t the world frame
        rpy -- initial orientation of the contact frame w.r.t the world frame
        Z -- half-height of the surface display box
        color -- color letter in ['r', 'g', 'b']
        name -- object's name (optional)
        pose -- initial pose (supersedes pos and rpy)
        visible -- initial box visibility
        """
        if not name:
            name = "Contact-%s" % str(uuid.uuid1())[0:3]
        self.friction = friction
        super(RectangularContact, self).__init__(
            env, X, Y, Z, pos=pos, rpy=rpy, color='r', name=name, pose=pose,
            visible=visible)

    @property
    def T(self):
        """Transformation matrix."""
        T = super(RectangularContact, self).T
        n = T[0:3, 2]
        T[0:3, 3] += self.Z * n
        return T

    @property
    def pose(self):
        """Pose (in OpenRAVE convention)."""
        pose = super(RectangularContact, self).pose
        pose[4:] += self.Z * self.n   # self.n calls self.T
        return pose

    @property
    def contact_points(self):
        """List of vertices of the contact area."""
        c1 = dot(self.T, array([+self.X, +self.Y, -self.Z, 1.]))[:3]
        c2 = dot(self.T, array([+self.X, -self.Y, -self.Z, 1.]))[:3]
        c3 = dot(self.T, array([-self.X, -self.Y, -self.Z, 1.]))[:3]
        c4 = dot(self.T, array([-self.X, +self.Y, -self.Z, 1.]))[:3]
        return [c1, c2, c3, c4]

    @property
    def gaf_span_world(self):
        """
        V-representation of the ground-applied force cone in world frame.
        """
        mu = self.friction
        f1 = dot(self.R, [+mu, +mu, -1])
        f2 = dot(self.R, [+mu, -mu, -1])
        f3 = dot(self.R, [-mu, +mu, -1])
        f4 = dot(self.R, [-mu, -mu, -1])
        return [f1, f2, f3, f4]

    @property
    def gaf_face_local(self):
        """
        H-representation of the ground-applied force cone in contact frame.
        """
        mu = self.friction
        l1 = [-1, 0, mu]
        l2 = [+1, 0, mu]
        l3 = [0, -1, mu]
        l4 = [0, +1, mu]
        return array([l1, l2, l3, l4])

    @property
    def gaf_face_world(self):
        """
        H-representation of the ground-applied force cone in world frame.
        """
        return dot(self.gaf_face_local, self.R.T)

    @property
    def gaw_face_local(self):
        """
        H-representation of the ground-applied wrench cone in contact frame.
        """
        X, Y = self.X, self.Y
        mu = self.friction
        grw_face = array([  # Ground Reaction Wrench Cone
            # fx  fy              fz  taux tauy tauz
            [-1,   0,            -mu,    0,   0,   0],
            [+1,   0,            -mu,    0,   0,   0],
            [0,   -1,            -mu,    0,   0,   0],
            [0,   +1,            -mu,    0,   0,   0],
            [0,    0,             -Y,   -1,   0,   0],
            [0,    0,             -Y,   +1,   0,   0],
            [0,    0,             -X,    0,  -1,   0],
            [0,    0,             -X,    0,  +1,   0],
            [-Y,  -X,  -(X + Y) * mu,  +mu,  +mu,  -1],
            [-Y,  +X,  -(X + Y) * mu,  +mu,  -mu,  -1],
            [+Y,  -X,  -(X + Y) * mu,  -mu,  +mu,  -1],
            [+Y,  +X,  -(X + Y) * mu,  -mu,  -mu,  -1],
            [+Y,  +X,  -(X + Y) * mu,  +mu,  +mu,  +1],
            [+Y,  -X,  -(X + Y) * mu,  +mu,  -mu,  +1],
            [-Y,  +X,  -(X + Y) * mu,  -mu,  +mu,  +1],
            [-Y,  -X,  -(X + Y) * mu,  -mu,  -mu,  +1]])
        gaw_face = grw_face
        gaw_face[:, (2, 3, 4)] *= -1  # oppose local Z-axis
        return gaw_face

    @property
    def gaw_face_world(self):
        """
        H-representation of the ground-applied wrench cone in world frame.
        """
        return dot(self.gaw_face_local, block_diag(self.R.T, self.R.T))


class RectangularContactSet(object):

    def __init__(self, contacts):
        """Create new contact set."""
        self.contacts = contacts

    @property
    def nb_contacts(self):
        """Number of contacts in set."""
        return len(self.contacts)

    def compute_grasp_matrix_from_forces(self):
        """
        Compute the grasp matrix from all contact points in the set.

        The grasp matrix G is such that

            w = dot(G, f_all),

        with w the contact wrench, and f_all the vector of contact *forces*
        (locomotion: from the environment onto the robot; grasping: from the
        hand onto the object).
        """
        G = zeros((6, 3 * 4 * self.nb_contacts))
        for i, contact in enumerate(self.contacts):
            for j, (x, y, z) in enumerate(contact.contact_points):
                Gi = array([
                    [1, 0, 0],
                    [0, 1, 0],
                    [0, 0, 1],
                    [0, -z, y],
                    [z, 0, -x],
                    [-y, x, 0]])
                G[:, (12 * i + 3 * j):(12 * i + 3 * (j + 1))] = Gi
        return G

    def compute_grasp_matrix_from_wrenches(self):
        """
        Compute the grasp matrix from all contact frames in the set.

        The grasp matrix G is such that

            w = dot(G, w_all),

        with w the contact wrench, and w_all the vector of contact *wrenches*
        (locomotion: from the environment onto the robot; grasping: from the
        hand onto the object).
        """
        G = zeros((6, 6 * self.nb_contacts))
        for i, contact in enumerate(self.contacts):
            x, y, z = contact.p
            Gi = array([
                [1, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, -z, y, 1, 0, 0],
                [z, 0, -x, 0, 1, 0],
                [-y, x, 0, 0, 0, 1]])
            G[:, (6 * i):(6 * (i + 1))] = Gi
        return G

    def compute_contact_forces(self, com, mass, comdd, camd, w_xy=.1, w_z=10.):
        """
        Compute a set of contact forces supporting a centroidal acceleration.

        If the centroidal acceleration (comdd, camd) can be supported by forces
        in the contact set, the solution that minimizes the cost

            sum_{contact i}  w_xy * |f_{i,xy}|^2 + w_z * |f_{i,z}|^2

        is selected, where |f_{i,xy}| is the norm of the x-y components (in
        local frame) of the i^th contact force.

        com -- position of the center of mass (COM)
        mass -- total mass of the system
        comdd -- acceleration of the COM
        camd -- rate of change of the angular momentum, taken at the COM
        w_xy -- weight given in the optimization to minimizing f_{xy}
        w_z -- weight given in the optimization to minimizing f_z
        """
        g = array([0., 0., -9.81])
        f_gi = mass * (g - comdd)
        tau_gi = cross(com, f_gi) - camd
        n = 12 * self.nb_contacts
        nb_forces = n / 3
        Pxy = block_diag(*[array([[1, 0, 0], [0, 1, 0], [0, 0, 0]])
                           for _ in xrange(nb_forces)])
        Pz = block_diag(*[array([[0, 0, 0], [0, 0, 0], [0, 0, 1]])
                          for _ in xrange(nb_forces)])
        oz = hstack([[0, 0, 1. / n] for _ in xrange(nb_forces)])
        Pz -= dot(oz.reshape((n, 1)), oz.reshape((1, n)))
        P = w_xy * Pxy + w_z * Pz
        RT = block_diag(*[contact.R.T for contact in
                          self.contacts for _ in xrange(4)])
        P = dot(RT.T, dot(P, RT))
        q = zeros((n,))
        G = block_diag(*[contact.gaf_face_world for contact in self.contacts
                         for _ in xrange(4)])
        h = zeros((G.shape[0],))
        A = self.compute_grasp_matrix_from_forces()
        b = hstack([f_gi, tau_gi])
        F = cvxopt_solve_qp(P, q, G, h, A, b)
        return -F