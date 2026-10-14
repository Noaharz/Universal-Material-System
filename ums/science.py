"""Scientific extensions (Phase 7).

Thermal and mechanical solvers, mixing models and a compact atomistic state for
large simulations. These features build on the definitions but never modify them:
definitions stay reusable, while states and solver results live at runtime.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .errors import UmsError
from .units import Quantity, resolve_unit


def _si(value: Any, unit_name: str) -> float:
    if value is None:
        raise UmsError(f"missing value for unit {unit_name}")
    if isinstance(value, Quantity):
        return value.to(resolve_unit(unit_name)).value
    return float(value)


@dataclass
class ThermalSolution1D:
    heat_flux: Quantity
    temperatures: List[float]
    positions: List[float]
    diffusivity: Optional[Quantity] = None
    duration: Optional[Quantity] = None

    @property
    def midpoint_temperature(self) -> float:
        return self.temperatures[len(self.temperatures) // 2]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heat_flux_W_per_m2": self.heat_flux.to(resolve_unit("W/m^2")).value,
            "midpoint_temperature_K": self.midpoint_temperature,
            "diffusivity_m2_per_s": self.diffusivity.to(resolve_unit("m^2/s")).value if self.diffusivity else None,
            "positions": self.positions,
            "temperatures": self.temperatures,
        }


class ThermalSolver:
    """1D Fourier heat-conduction solver."""

    def __init__(
        self,
        conductivity: Quantity,
        density: Optional[Quantity] = None,
        heat_capacity: Optional[Quantity] = None,
    ):
        self.conductivity = conductivity
        self.density = density
        self.heat_capacity = heat_capacity

    @classmethod
    def from_material(cls, resolved: Any) -> "ThermalSolver":
        conductivity = resolved.resolve_property("ThermalConductivity")
        if conductivity is None:
            raise UmsError(f"material {resolved.id!r} has no ThermalConductivity")
        return cls(
            conductivity=conductivity,
            density=resolved.resolve_property("Density"),
            heat_capacity=resolved.resolve_property("HeatCapacity"),
        )

    @property
    def thermal_diffusivity(self) -> Optional[Quantity]:
        if self.density is None or self.heat_capacity is None:
            return None
        k = _si(self.conductivity, "W/(m*K)")
        rho = _si(self.density, "kg/m^3")
        cp = _si(self.heat_capacity, "J/(kg*K)")
        return Quantity(k / (rho * cp), resolve_unit("m^2/s"))

    def steady_state_1d(
        self,
        length: Quantity,
        t_left: Quantity,
        t_right: Quantity,
        samples: int = 11,
    ) -> ThermalSolution1D:
        """Steady-state conduction through a slab (q = k * dT / L)."""
        if samples < 2:
            raise UmsError("samples must be >= 2")
        k = _si(self.conductivity, "W/(m*K)")
        length_m = _si(length, "m")
        tl = _si(t_left, "K")
        tr = _si(t_right, "K")
        flux = k * (tr - tl) / length_m
        positions = [length_m * i / (samples - 1) for i in range(samples)]
        temperatures = [tl + (tr - tl) * i / (samples - 1) for i in range(samples)]
        return ThermalSolution1D(
            heat_flux=Quantity(abs(flux), resolve_unit("W/m^2")),
            temperatures=temperatures,
            positions=positions,
            diffusivity=self.thermal_diffusivity,
        )

    def transient_1d(
        self,
        length: Quantity,
        t_initial: Quantity,
        t_left: Quantity,
        t_right: Quantity,
        duration: Quantity,
        n_cells: int = 50,
    ) -> ThermalSolution1D:
        """Explicit finite-difference transient conduction (FTCS)."""
        diffusivity = self.thermal_diffusivity
        if diffusivity is None:
            raise UmsError("transient solver needs Density and HeatCapacity")
        if n_cells < 3:
            raise UmsError("n_cells must be >= 3")
        alpha = diffusivity.to(resolve_unit("m^2/s")).value
        length_m = _si(length, "m")
        duration_s = _si(duration, "s")
        dx = length_m / (n_cells - 1)
        # stable timestep for the explicit scheme
        dt = 0.4 * dx * dx / alpha
        n_steps = max(1, int(math.ceil(duration_s / dt)))
        dt = duration_s / n_steps

        tl = _si(t_left, "K")
        tr = _si(t_right, "K")
        t0 = _si(t_initial, "K")
        temps = [t0] * n_cells
        temps[0] = tl
        temps[-1] = tr
        r = alpha * dt / (dx * dx)
        for _ in range(n_steps):
            new = list(temps)
            for i in range(1, n_cells - 1):
                new[i] = temps[i] + r * (temps[i + 1] - 2 * temps[i] + temps[i - 1])
            new[0] = tl
            new[-1] = tr
            temps = new
        positions = [dx * i for i in range(n_cells)]
        flux = self.conductivity.to(resolve_unit("W/(m*K)")).value * (tl - tr) / length_m
        return ThermalSolution1D(
            heat_flux=Quantity(abs(flux), resolve_unit("W/m^2")),
            temperatures=temps,
            positions=positions,
            diffusivity=diffusivity,
            duration=Quantity(duration_s, resolve_unit("s")),
        )


@dataclass
class MechanicalSolution:
    strain: float
    stress: Quantity
    youngs_modulus: Quantity
    poisson_ratio: float
    shear_modulus: Quantity
    bulk_modulus: Quantity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strain": self.strain,
            "stress_Pa": self.stress.to(resolve_unit("Pa")).value,
            "youngs_modulus_GPa": self.youngs_modulus.to(resolve_unit("GPa")).value,
            "poisson_ratio": self.poisson_ratio,
            "shear_modulus_GPa": self.shear_modulus.to(resolve_unit("GPa")).value,
            "bulk_modulus_GPa": self.bulk_modulus.to(resolve_unit("GPa")).value,
        }


class MechanicalSolver:
    """Isotropic linear elasticity (Hooke's law)."""

    def __init__(self, youngs_modulus: Quantity, poisson_ratio: Quantity):
        self.youngs_modulus = youngs_modulus
        if isinstance(poisson_ratio, Quantity):
            self.poisson_ratio = poisson_ratio.si_value
        else:
            self.poisson_ratio = float(poisson_ratio)

    @classmethod
    def from_material(cls, resolved: Any) -> "MechanicalSolver":
        e = resolved.resolve_property("YoungsModulus")
        if e is None:
            raise UmsError(f"material {resolved.id!r} has no YoungsModulus")
        nu = resolved.resolve_property("PoissonRatio") or Quantity(0.3)
        return cls(e, nu)

    @property
    def shear_modulus(self) -> Quantity:
        e = _si(self.youngs_modulus, "Pa")
        g = e / (2 * (1 + self.poisson_ratio))
        return Quantity(g, resolve_unit("Pa"))

    @property
    def bulk_modulus(self) -> Quantity:
        e = _si(self.youngs_modulus, "Pa")
        k = e / (3 * (1 - 2 * self.poisson_ratio))
        return Quantity(k, resolve_unit("Pa"))

    def uniaxial(self, stress: Quantity) -> MechanicalSolution:
        e = _si(self.youngs_modulus, "Pa")
        sigma = _si(stress, "Pa")
        strain = sigma / e
        return MechanicalSolution(
            strain=strain,
            stress=stress,
            youngs_modulus=self.youngs_modulus,
            poisson_ratio=self.poisson_ratio,
            shear_modulus=self.shear_modulus,
            bulk_modulus=self.bulk_modulus,
        )


class MixingModel:
    """Combining properties of several materials.

    Not every mixture is a linear combination, so callers must choose an
    appropriate model instead of assuming linear behaviour.
    """

    def __init__(self, kind: str = "linear"):
        self.kind = kind

    def combine(self, values: Sequence[Tuple[Quantity, float]]) -> Quantity:
        if not values:
            raise UmsError("no components to mix")
        if self.kind == "linear":
            unit = values[0][0].unit
            total = 0.0
            for quantity, fraction in values:
                total += quantity.to(unit).value * fraction
            return Quantity(total, unit)
        if self.kind == "harmonic":
            unit = values[0][0].unit
            total = 0.0
            for quantity, fraction in values:
                value = quantity.to(unit).value
                if value != 0:
                    total += fraction / value
            return Quantity(1.0 / total, unit)
        if self.kind == "geometric":
            unit = values[0][0].unit
            product = 1.0
            for quantity, fraction in values:
                product *= quantity.to(unit).value ** fraction
            return Quantity(product, unit)
        raise UmsError(f"unknown mixing model: {self.kind!r}")

    @staticmethod
    def density_from_mass_fractions(values: Sequence[Tuple[Quantity, float]]) -> Quantity:
        """Density from mass fractions: 1/rho = sum(w_i / rho_i)."""
        if not values:
            raise UmsError("no components to mix")
        unit = values[0][0].unit
        inv = 0.0
        for quantity, fraction in values:
            inv += fraction / quantity.to(unit).value
        return Quantity(1.0 / inv, unit)


class AtomisticState:
    """Compact array-style state for atomistic simulations.

    Stores species indices, positions and optional velocities for a large number
    of atoms without creating one object per atom or one file per atom.
    """

    def __init__(
        self,
        species: Optional[List[int]] = None,
        positions: Optional[List[Tuple[float, float, float]]] = None,
        velocities: Optional[List[Tuple[float, float, float]]] = None,
        box: Optional[Tuple[float, float, float]] = None,
    ):
        self.species: List[int] = list(species or [])
        self.positions: List[Tuple[float, float, float]] = list(positions or [])
        self.velocities: List[Tuple[float, float, float]] = list(velocities or [])
        self.box = box

    @property
    def n_atoms(self) -> int:
        return len(self.species)

    def add_atom(self, species_index: int, position: Tuple[float, float, float], velocity: Optional[Tuple[float, float, float]] = None) -> int:
        self.species.append(species_index)
        self.positions.append(position)
        self.velocities.append(velocity or (0.0, 0.0, 0.0))
        return self.n_atoms - 1

    @classmethod
    def from_structure(cls, structure: Any, manager: Any = None, repeats: Tuple[int, int, int] = (1, 1, 1)) -> "AtomisticState":
        """Build a state by tiling a structure's basis on a lattice."""
        lattice = None
        if structure.crystal:
            lattice_value = structure.crystal.get("LatticeParameter")
            if isinstance(lattice_value, Quantity):
                lattice = lattice_value.to(resolve_unit("m")).value
        if lattice is None:
            lattice = 1e-10
        basis = []
        species_map: Dict[str, int] = {}
        for atom in structure.atoms:
            ref = str(atom.get("Type"))
            if ref not in species_map:
                species_map[ref] = len(species_map)
            basis.append((species_map[ref], atom))
        if not basis:
            for entry in structure.composition:
                ref = str(entry.get("AtomRef"))
                if ref not in species_map:
                    species_map[ref] = len(species_map)
                basis.append((species_map[ref], {"Type": ref}))
        state = cls(box=(lattice * repeats[0], lattice * repeats[1], lattice * repeats[2]))
        for i in range(repeats[0]):
            for j in range(repeats[1]):
                for k in range(repeats[2]):
                    for species_index, _atom in basis:
                        state.add_atom(
                            species_index,
                            (i * lattice, j * lattice, k * lattice),
                        )
        return state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_atoms": self.n_atoms,
            "species": self.species[:10],
            "box": self.box,
        }
