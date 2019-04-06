# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- IK: can now take joint acceleration limits into account
- IK: upgraded with Levenberg-Marquardt damping
- IK: warm-start parameter to ``solve()``
- Robot model gets a ``get_link()`` function
- Simulation gets ``set_camera_transform()`` function
- This change log
- ZMP support areas can now take optional contact pressure limits

### Fixed

- IK: singularity fix from [Pfeiffer et al.](https://doi.org/10.1109/LRA.2018.2855265)
- Knee joint names in JVRC-1 model
- Restore initial settings in IK solve()

### Changed

- GUI: default point size is now 1 cm
- GUI: renamed ``draw_polyhedron()`` to ``draw_polytope()``
- IK: task strings now print both weight and gain coefficients
- Stances now bind end-effector links as well

## [1.0.0] - 2018/10/17

### Added
- Initial release of the project. Let's take it from there.