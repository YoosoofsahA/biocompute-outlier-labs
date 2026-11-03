"""Shared dish helpers: simulator setup, stimulation and spike counting. Owner: role 4 (Dish runner)."""
from __future__ import annotations

import cl

STIM = cl.StimDesign(200, -1.5, 200, 1.5)   # biphasic, cathodic first, 0.3 nC per phase
BURST_HZ = 100                              # pulses 10 ms apart, so each can fire the neuron
RESERVED = frozenset({0, 4, 7, 56, 63})
TICKS_PER_SECOND = 20
TICKS_PER_CHECK = 40                        # one test frame every 2 s (oddball: rare test, frequent fresh reference)
COUNT_TICKS = (1, 2)                        # response window: the 100 ms after the stim on tick 0
REFERENCE_TICKS = (10, 20, 30)              # fresh reference re-shown here, not counted


def sim_config(seed: int, coupling_mV: float, adaptation_mV: float | None, adaptation_tau_ms: float | None) -> dict:
    """Build the LIF source config. Adaptation keys are only sent once role 1's simulator change supports them."""
    config: dict = {"random_seed": seed, "coupling_gain_mV": coupling_mV}
    if adaptation_mV is not None:
        config["adaptation_mV"] = adaptation_mV
    if adaptation_tau_ms is not None:
        config["adaptation_tau_ms"] = adaptation_tau_ms
    return config


def use_lif(config: dict) -> None:
    """Select the LIF simulator with `config`. Does nothing on a CL1."""
    if cl.is_simulator():
        cl.sim.set_simulator_data_source("organoid_simulator.lif_data_source:make_lif_source", config=config)


def stimulate(neurons, pattern: dict[int, int]) -> None:
    """Deliver `pattern` (electrode -> pulse count) as one 100 Hz train per electrode.

    Raises:
        ValueError: If the pattern uses a reserved channel.
    """
    bad = RESERVED.intersection(pattern)
    if bad:
        raise ValueError(f"pattern stimulates reserved channels {sorted(bad)}")
    for channel, count in pattern.items():
        if count > 0:
            neurons.stim(cl.ChannelSet(channel), STIM, cl.BurstDesign(count, BURST_HZ))
