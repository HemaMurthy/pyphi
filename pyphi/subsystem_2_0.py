#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# subsystem_2_0.py

"""Implementation of IIT 2.0

All page numbers and figures reference the IIT 2.0 paper:

`Integrated Information in Discrete Dynamical Systems: Motivation and
Theoretical Framework <https://doi.org/10.1371/journal.pcbi.1000091>`_
by David Balduzzi and Giulio Tononi.
"""

import collections
import functools
import itertools

import numpy as np
from scipy.stats import entropy as _entropy

import pyphi
from pyphi.distribution import flatten, max_entropy_distribution
from pyphi.models import cmp
from pyphi.partition import bipartition


def entropy(pk, qk=None):
    """Entropy, measured in bits."""
    return _entropy(flatten(pk), flatten(qk), base=2.0)


class Subsystem_2_0:

    def __init__(self, network, state, node_indices):
        self.network = network
        self.state = tuple(state)
        self.node_indices = node_indices

        # IIT 3.0 subsystem used to compute cause repertoires
        # Note that external elements are *not* frozen - that is handled
        # by the `_external_indices=()` argument.
        self._subsystem_3_0 = pyphi.Subsystem(
            self.network, self.state, self.node_indices, _external_indices=())

    def __len__(self):
        return len(self.node_indices)

    def __repr__(self):
        return "Subsystem2.0(state={}, nodes={})".format(self.state,
                                                         self.node_indices)

    def prior_repertoire(self, mechanism=None):
        """The a priori repertoire of the system."""
        if mechanism is None:
            mechanism = self.node_indices
        return max_entropy_distribution(mechanism, len(self))

    def posterior_repertoire(self, mechanism=None):
        """The a posteriori repertoire of the system."""
        if mechanism is None:
            mechanism = self.node_indices
        return self._subsystem_3_0.cause_repertoire(mechanism, mechanism)

    def partitioned_posterior_repertoire(self, partition):
        return functools.reduce(np.multiply, [
            self.posterior_repertoire(mechanism) for mechanism in partition])

    def effective_information(self, mechanism=None):
        """The effective information of the system."""
        return entropy(self.posterior_repertoire(mechanism),
                       self.prior_repertoire(mechanism))

    def effective_information_partition(self, partition):
        """The effective information across an arbitrary partition.

        The total partition is a special case; otherwise it would produce
        partitioned effective information of 0. See p. 5-6.
        """
        assert partition.indices == self.node_indices

        if partition.is_total:
            return self.effective_information()

        return entropy(self.posterior_repertoire(),
                       self.partitioned_posterior_repertoire(partition))

    def find_mip(self):
        """Compute the minimum information partition of the system."""
        return min(Mip_2_0(self.effective_information_partition(partition),
                           partition, self)
                   for partition in generate_partitions(self.node_indices))

    def phi(self):
        """The integrated information of the system."""
        return self.find_mip().ei


@functools.total_ordering
class Mip_2_0:

    def __init__(self, ei, partition, subsystem):
        self.ei = ei
        self.partition = partition
        self.subsystem = subsystem

    @property
    def ei_normalized(self):
        return self.ei / self.partition.normalization

    @cmp.sametype
    def __eq__(self, other):
        return (self.ei == other.ei and self.partition == other.partition)

    @cmp.sametype
    def __lt__(self, other):
        """If more than one partition has the same minimum normalized value,
        select the partition that generates the lowest _un-normalized_
        quantity of effective information.
        """
        return (self.ei_normalized, self.ei) < (other.ei_normalized, other.ei)

    def __repr__(self):
        return "Mip2.0(ei={}, {})".format(self.ei, self.partition)


# TODO: implement all partitions
def generate_partitions(node_indices):
    """Currently only returns bipartitions."""
    for partition in bipartition(node_indices):
        # Hack to turn ((), (1, 2, ..)) into the total partition
        if partition[0] == ():
            partition = (partition[1],)
        yield Partition(*partition)


class Partition(collections.abc.Sequence):

    def __init__(self, *parts):
        self.parts = tuple(sorted(parts))

    def __len__(self):
        return len(self.parts)

    def __getitem__(self, x):
        return self.parts[x]

    @cmp.sametype
    def __eq__(self, other):
        return self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)

    def __repr__(self):
        return "Partition{}".format(self.parts)

    @property
    def indices(self):
        return tuple(sorted(itertools.chain.from_iterable(self.parts)))

    @property
    def normalization(self):
        """Normalization factor for this partition.

        See p. 6-7 for a discussion.
        """
        if self.is_total:
            return len(self.indices)
        return (len(self) - 1) * min(len(p) for p in self)

    @property
    def is_total(self):
        """Is this a total (unitary) partition?"""
        return len(self) == 1