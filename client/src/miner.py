from scapy.sendrecv import sr
import random
import math

from .container import TracerouteVertex, BlackHoleVertex, TracerouteHop
from .stats import probes_for_vertex


class DiamondMiner:
    """A hop-by-hop variation of the existing diamond miner algorithm."""

    def __init__(self, traceroute, inter, timeout, retry, abort):
        self.traceroute = traceroute
        self.inter = inter
        assert self.inter >= 0
        self.timeout = timeout
        assert self.timeout > 0
        self.retry = retry
        self.abort = abort
        assert self.abort >= 2

    def _next_flow(self):
        """Generates a pseudo-random uniform flow identifier in the range
        between 10000 and 65535."""
        return int(random.uniform(10000, 65535))

    def _generate_flows(self, hop):
        """Generates flow identifiers to be used for the current hop.
        First all previously used identifiers are returned vertex by vertex.
        If they are exhausted, new identifiers are generated."""
        prev_flows = hop.flows
        yield from prev_flows
        while True:
            flow = self._next_flow()
            if flow not in prev_flows:
                prev_flows.add(flow)
                yield flow

    def _send_probes_to_hop(self, hop, flows):
        """Sends probes with a given ttl and flows."""
        ttl = hop.ttl

        unresp_counter = 0
        unresp_flows = set(flows)
        while unresp_flows:
            flow_list = list(unresp_flows)
            probes = [self.traceroute.create_probe(ttl, flow) for flow in flow_list]

            ans, unans = sr(
                probes, inter=self.inter, timeout=self.timeout  # , verbose=0
            )

            for req, resp in ans:
                flow = flow_list[probes.index(req)]
                address, rtt = self.traceroute.parse_probe_response(req, resp)
                vertex = TracerouteVertex(address)

                if vertex not in hop:
                    hop.add(vertex)
                hop[vertex].update(flow, rtt)
                unresp_flows.discard(flow)

            if unresp_counter >= abs(self.retry):
                break

            if ans and self.retry < 0:
                unresp_counter = 0
            else:
                unresp_counter += 1

    def _probe_and_update(self, hop, next_hop, flows):
        """Sends probes with a given ttl and flows and updates the vertices
        with relevant information, such as rtt and responding flows."""
        if len(hop) == 1:
            hop.first().flow_set.update(flows)

        n_hops = len(next_hop)

        self._send_probes_to_hop(hop, flows - hop.flows)
        self._send_probes_to_hop(next_hop, flows)

        for vertex in hop:
            for next_vertex in next_hop:
                if vertex.flow_set & next_vertex.flow_set:
                    vertex.add_successor(next_vertex)

        return len(next_hop) - n_hops > 0

    def _nprobes(self, alpha, hop):
        """Computes the number of flows needed for the next hop depending
        on the certainty alpha and the current set of vertices."""
        probes = lambda v: probes_for_vertex(max(1, len(v.successors)) + 1, alpha)

        total_flows = len(hop.flows)
        max_probes = 0
        for vertex in hop:
            denominator = len(vertex.flow_set) / total_flows if vertex.flow_set else 1
            result = math.ceil(probes(vertex) / denominator)
            if result > max_probes:
                max_probes = result
        return max_probes

    def discover(self, alpha, first_hop, min_ttl, max_ttl, target=None):
        assert alpha > 0 and alpha < 1
        assert min_ttl > 0 and max_ttl >= min_ttl

        root = TracerouteVertex(first_hop)
        addresses = lambda hop: set(v.address for v in hop)
        hop = TracerouteHop(0, [root])

        unresponsive = 0
        last_known_vertex = None

        for ttl in range(min_ttl, max_ttl + 1):
            print(f"Probing TTL {ttl}...")
            next_hop = TracerouteHop(ttl)
            iter_flows = self._generate_flows(hop)

            start = 0
            stop = self._nprobes(alpha, hop)
            while stop > start:
                flows = set(next(iter_flows) for _ in range(start, stop))
                if not self._probe_and_update(hop, next_hop, flows):
                    break

                start = stop
                stop = self._nprobes(alpha, hop)

            # Connect all vertices without successors to a newly created
            # black hole, which inherits the flows of its predecessors.
            # Thus we can chain multiple black holes by flow inheritance,
            # which can be reconnected once a successor vertex with a matching flow is found.
            dangling_vertices = [v for v in hop if not v.successors]
            if dangling_vertices:
                black_hole = BlackHoleVertex()
                next_hop.add(black_hole)
                for v in dangling_vertices:
                    v.add_successor(black_hole)
                    black_hole.flow_set.update(v.flow_set)

            # Check if the abort condition is met.
            # If multiple successive black holes possibly intermixed with a single vertex
            # are found, increment the unresponsive counter.
            if len(next_hop) == 1:
                next_vertex = next_hop.first()
                if target and next_vertex.address == target:
                    last_known_vertex = None
                    break

                if isinstance(next_vertex, BlackHoleVertex):
                    unresponsive += 1
                elif next_vertex == last_known_vertex:
                    unresponsive += 1
                else:
                    unresponsive = 0
                    last_known_vertex = next_vertex
            else:
                unresponsive = 0
                last_known_vertex = None

            if unresponsive >= self.abort:
                break

            hop = next_hop

        # Track back to the last known vertex and disconnect
        # successive black holes if such a vertex is known.
        if last_known_vertex is not None:
            last_known_vertex.successors.clear()
        return root
