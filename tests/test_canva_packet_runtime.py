from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import PacketRuntime


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


if __name__ == "__main__":
    unittest.main()
