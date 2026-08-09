from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    MAX_REPLAY_BYTES,
    PacketRuntime,
    decode_packet_replay,
    encode_packet_replay,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class PacketRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.events = []
        self.runtime = PacketRuntime(
            clock=self.clock,
            event_sink=lambda event, ticket: self.events.append(
                (event.event, ticket.status)
            ),
        )

    def test_ticket_lifecycle_payload_metadata_and_trace(self) -> None:
        ticket = self.runtime.create(
            "msg-1",
            "edge-in",
            payload={"temperature": 42},
            metadata={"source": "sensor"},
            priority=7,
            ttl=5,
            timeout=4.0,
        )
        self.runtime.start_segment(ticket.message_id, "edge-in")
        self.clock.advance(0.4)
        self.runtime.arrive_segment(ticket.message_id, "edge-in")
        self.runtime.start_segment(ticket.message_id, "edge-out")
        self.runtime.arrive_segment(ticket.message_id, "edge-out")
        self.runtime.complete(ticket.message_id, "edge-out")

        snapshot = ticket.snapshot(self.clock())
        self.assertEqual("completed", snapshot["status"])
        self.assertEqual({"temperature": 42}, snapshot["payload"])
        self.assertEqual("sensor", snapshot["metadata"]["source"])
        self.assertEqual(2, snapshot["hopCount"])
        self.assertEqual(["edge-in", "edge-out"], snapshot["visited"])
        self.assertEqual(
            [
                "created", "segment_started", "segment_arrived",
                "segment_started", "segment_arrived", "completed",
            ],
            [event.event for event in self.runtime.trace(message_id="msg-1")],
        )

    def test_priority_order_branch_policies_and_ttl(self) -> None:
        low = self.runtime.create("low", "input", priority=1, branch_policy="all")
        high = self.runtime.create(
            "high", "input", priority=20, branch_policy="round-robin", ttl=1
        )
        self.assertEqual(["high", "low"], [ticket.message_id for ticket in self.runtime.tickets()])
        self.assertEqual(
            ("a", "b"), self.runtime.select_branches(low.message_id, ("a", "b"))
        )
        self.assertEqual(("a",), self.runtime.select_branches(high.message_id, ("a", "b")))
        self.assertEqual(("b",), self.runtime.select_branches(high.message_id, ("a", "b")))
        self.runtime.start_segment(high.message_id, "input")
        self.runtime.arrive_segment(high.message_id, "input")
        failed = self.runtime.start_segment(high.message_id, "next")
        self.assertEqual("failed", failed.status)
        self.assertIn("TTL", failed.error)

    def test_pause_breakpoint_timeout_cancel_and_clear(self) -> None:
        ticket = self.runtime.create("break", "edge", timeout=2.0)
        self.runtime.start_segment(ticket.message_id, "edge")
        self.runtime.set_breakpoint("edge", True)
        self.assertTrue(self.runtime.should_break("edge", ticket.message_id))
        self.runtime.breakpoint_hit("edge", ticket.message_id)
        self.assertTrue(self.runtime.paused)
        self.assertEqual("paused", ticket.status)
        self.assertTrue(self.runtime.resume())
        self.assertEqual("in_flight", ticket.status)
        self.clock.advance(2.1)
        self.assertEqual("timed_out", self.runtime.expire()[0].status)

        cancelled = self.runtime.create("cancel", "edge")
        self.runtime.cancel(cancelled.message_id, "User stopped it")
        self.assertEqual("cancelled", cancelled.status)
        self.assertEqual(2, self.runtime.clear_completed())
        self.assertFalse(self.runtime.tickets())

    def test_validation_and_bounded_trace(self) -> None:
        runtime = PacketRuntime(clock=self.clock, max_trace_events=10)
        with self.assertRaisesRegex(ValueError, "branch policy"):
            runtime.create("bad", "edge", branch_policy="unknown")
        with self.assertRaisesRegex(ValueError, "TTL"):
            runtime.create("bad", "edge", ttl=0)
        with self.assertRaisesRegex(ValueError, "timeout"):
            runtime.create("bad", "edge", timeout=0)
        for index in range(12):
            ticket = runtime.create(f"m{index}", "edge")
            runtime.cancel(ticket.message_id)
        self.assertEqual(10, len(runtime.trace()))

    def test_one_thousand_concurrent_tickets_remain_addressable(self) -> None:
        runtime = PacketRuntime(clock=self.clock, max_trace_events=5000)
        for index in range(1000):
            ticket = runtime.create(
                f"bulk-{index}", "ingress", priority=index % 10
            )
            runtime.start_segment(ticket.message_id, "ingress")
        self.assertEqual(1000, len(runtime.tickets(include_completed=False)))
        self.assertEqual(9, runtime.tickets()[0].priority)
        for ticket in runtime.tickets(include_completed=False):
            runtime.arrive_segment(ticket.message_id, "ingress")
            runtime.complete(ticket.message_id, "ingress")
        self.assertFalse(runtime.tickets(include_completed=False))
        self.assertEqual(1000, runtime.clear_completed())

    def test_replay_fixture_round_trip_and_divergence_comparison(self) -> None:
        ticket = self.runtime.create(
            "original", "edge-a", payload={"value": 7},
            metadata={"topic": "demo"}, priority=4, branch_policy="first",
        )
        self.runtime.start_segment(ticket.message_id, "edge-a")
        self.clock.advance(0.25)
        self.runtime.arrive_segment(ticket.message_id, "edge-a")
        self.runtime.complete(ticket.message_id, "edge-a")

        fixture = self.runtime.capture_replay("original", fixture_id="fixture-a")
        restored = decode_packet_replay(encode_packet_replay(fixture))
        self.assertEqual(fixture, restored)
        self.assertTrue(self.runtime.compare_replay(restored, "original").matched)
        self.assertNotIn("timestamp", restored.expected_events[0])
        self.assertEqual(0.0, restored.expected_events[0]["offset"])

        divergent = self.runtime.create("divergent", "edge-a", payload={"value": 7})
        self.runtime.start_segment(divergent.message_id, "edge-b")
        self.runtime.arrive_segment(divergent.message_id, "edge-b")
        self.runtime.complete(divergent.message_id, "edge-b")
        comparison = self.runtime.compare_replay(restored, "divergent")
        self.assertFalse(comparison.matched)
        self.assertIn("event sequence diverged", comparison.mismatches)

    def test_link_metrics_pair_latency_throughput_and_terminal_drops(self) -> None:
        delivered = self.runtime.create("delivered", "edge")
        self.runtime.start_segment(delivered.message_id, "edge")
        self.clock.advance(0.4)
        self.runtime.arrive_segment(delivered.message_id, "edge")
        self.runtime.complete(delivered.message_id, "edge")

        timed_out = self.runtime.create("timeout", "edge", timeout=1.0)
        self.runtime.start_segment(timed_out.message_id, "edge")
        self.clock.advance(1.1)
        self.runtime.expire()

        metric = self.runtime.link_metrics("edge", window=2.0)[0]
        self.assertEqual(2, metric["started"])
        self.assertEqual(1, metric["arrived"])
        self.assertEqual(1, metric["timedOut"])
        self.assertEqual(0, metric["inFlight"])
        self.assertAlmostEqual(0.5, metric["deliveryRate"])
        self.assertAlmostEqual(400.0, metric["latencyMs"]["average"])
        self.assertAlmostEqual(0.5, metric["throughputPerSecond"])
        self.assertEqual(1, self.runtime.reset_link_metrics("edge"))
        self.assertFalse(self.runtime.link_metrics())

    def test_replay_boundary_rejects_oversized_and_non_json_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "too large"):
            decode_packet_replay(b"x" * (MAX_REPLAY_BYTES + 1))
        ticket = self.runtime.create("not-portable", "edge", payload=object())
        self.runtime.start_segment(ticket.message_id, "edge")
        self.runtime.arrive_segment(ticket.message_id, "edge")
        self.runtime.complete(ticket.message_id, "edge")
        with self.assertRaisesRegex(TypeError, "Replay payload"):
            self.runtime.capture_replay(ticket.message_id)


if __name__ == "__main__":
    unittest.main()
