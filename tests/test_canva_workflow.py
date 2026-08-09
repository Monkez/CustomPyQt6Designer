from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    WorkflowBackpressureError,
    WORKFLOW_COMPONENT_DEFINITIONS,
    WORKFLOW_COMPONENT_TYPES,
    WorkflowExecutor,
    WorkflowGraph,
)


def workflow_document(elements, connectors):
    return {
        "elements": elements,
        "connectors": connectors,
    }


def node(node_id, type_id, ports, **workflow):
    return {
        "id": node_id,
        "type": type_id,
        "ports": [
            {"id": port_id, "mode": "free", "side": "bottom"}
            for port_id in ports
        ],
        "workflow": workflow,
    }


def edge(edge_id, source, target, source_port="out", target_port="in"):
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "sourcePort": source_port,
        "targetPort": target_port,
    }


class WorkflowKernelTests(unittest.TestCase):
    def test_opt_in_pack_defines_every_planned_runtime_component(self) -> None:
        self.assertEqual(
            WORKFLOW_COMPONENT_TYPES,
            tuple(definition.type_id for definition in WORKFLOW_COMPONENT_DEFINITIONS),
        )
        self.assertEqual(len(WORKFLOW_COMPONENT_TYPES), len(set(WORKFLOW_COMPONENT_TYPES)))
        for definition in WORKFLOW_COMPONENT_DEFINITIONS:
            self.assertEqual("monkez.workflow", definition.plugin_id)
            self.assertIn("workflow", definition.capabilities)
            self.assertIn("ports", definition.capabilities)
            self.assertTrue(definition.defaults["ports"])

    def test_transform_filter_splitter_and_sinks_execute_end_to_end(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [
                node("source", "wf_source", ("out",)),
                node("transform", "wf_transform", ("in", "out"), operation="scale", value=2),
                node("filter", "wf_filter", ("in", "out", "rejected"), operator="gt", value=10),
                node("split", "wf_splitter", ("in", "out-1", "out-2")),
                node("accepted-a", "wf_sink", ("in",)),
                node("accepted-b", "wf_sink", ("in",)),
                node("rejected", "wf_sink", ("in",)),
            ],
            [
                edge("e1", "source", "transform"),
                edge("e2", "transform", "filter"),
                edge("e3", "filter", "split", "out"),
                edge("e4", "filter", "rejected", "rejected"),
                edge("e5", "split", "accepted-a", "out-1"),
                edge("e6", "split", "accepted-b", "out-2"),
            ],
        ))
        executor = WorkflowExecutor(graph)
        executor.start("source", 7, token_id="accepted")
        executor.start("source", 3, token_id="rejected")
        result = executor.run_until_idle()

        self.assertEqual("completed", result.state)
        self.assertEqual((14.0,), result.outputs["accepted-a"])
        self.assertEqual((14.0,), result.outputs["accepted-b"])
        self.assertEqual((6.0,), result.outputs["rejected"])
        self.assertFalse(result.errors)
        self.assertIn("connector_emitted", [event.event for event in executor.trace()])

    def test_switch_delay_debounce_throttle_and_logical_time(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [
                node("switch", "wf_switch", ("in", "true", "false"), field="enabled", operator="truthy"),
                node("delay", "wf_delay", ("in", "out"), seconds=2.5),
                node("debounce", "wf_debounce", ("in", "out"), interval=0.5),
                node("throttle", "wf_throttle", ("in", "out"), interval=1.0),
                node("yes", "wf_sink", ("in",)),
                node("no", "wf_sink", ("in",)),
            ],
            [
                edge("true", "switch", "delay", "true"),
                edge("false", "switch", "no", "false"),
                edge("delay-debounce", "delay", "debounce"),
                edge("debounce-throttle", "debounce", "throttle"),
                edge("throttle-sink", "throttle", "yes"),
            ],
        ))
        executor = WorkflowExecutor(graph, clock=lambda: 10.0)
        executor.enqueue("switch", {"enabled": True, "value": 1}, token_id="one")
        executor.enqueue("switch", {"enabled": True, "value": 2}, token_id="two")
        executor.enqueue("switch", {"enabled": False, "value": 3}, token_id="three")
        result = executor.run_until_idle()

        self.assertEqual(13.0, result.logical_time)
        self.assertEqual(({"enabled": False, "value": 3},), result.outputs["no"])
        self.assertEqual(({"enabled": True, "value": 2},), result.outputs["yes"])
        self.assertIn("token_debounced", [event.event for event in executor.trace()])

    def test_retry_custom_handler_and_error_edge(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [
                node("retry", "wf_retry", ("in", "out", "error"), retries=2, retryDelay=0.1),
                node("sink", "wf_sink", ("in",)),
                node("errors", "wf_error_handler", ("error",)),
            ],
            [
                edge("success", "retry", "sink", "out"),
                edge("failure", "retry", "errors", "error", "error"),
            ],
        ))
        executor = WorkflowExecutor(graph, clock=lambda: 0.0)
        calls = []

        def flaky(context, payload):
            calls.append(context.attempt)
            if context.attempt < 2:
                raise RuntimeError("temporary")
            return payload

        executor.register_handler("retry", flaky, node=True)
        executor.enqueue("retry", {"ok": True}, token_id="retry-token")
        result = executor.run_until_idle()
        self.assertEqual([0, 1, 2], calls)
        self.assertEqual(({"ok": True},), result.outputs["sink"])
        self.assertEqual("completed", result.state)

        failed = WorkflowExecutor(graph, clock=lambda: 0.0)
        failed.register_handler(
            "retry", lambda _context, _payload: (_ for _ in ()).throw(ValueError("bad")),
            node=True,
        )
        failed.enqueue("retry", "broken", token_id="failed-token")
        failure = failed.run_until_idle()
        self.assertEqual("failed", failure.state)
        self.assertEqual("ValueError", failure.outputs["errors"][0]["type"])
        self.assertTrue(failure.errors[0]["handled"])
        self.assertEqual("monkez.workflow.failure", failure.errors[0]["format"])
        self.assertIn("failure_routed", [event.event for event in failed.trace()])

    def test_counter_state_machine_and_one_thousand_tokens(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [
                node("counter", "wf_counter", ("in", "out"), field="sequence", step=1),
                node(
                    "machine", "wf_state_machine", ("in", "out", "changed"),
                    initial="idle", eventField="event", stateField="state",
                    transitions={"idle": {"start": "running"}, "running": {"stop": "idle"}},
                ),
                node("sink", "wf_sink", ("in",)),
            ],
            [
                edge("counter-machine", "counter", "machine"),
                edge("machine-sink", "machine", "sink", "changed"),
            ],
        ))
        executor = WorkflowExecutor(graph, clock=lambda: 0.0, max_steps=5000)
        for index in range(1000):
            executor.enqueue(
                "counter", {"event": "start" if index == 0 else "noop"},
                token_id=f"bulk-{index}", priority=index % 5,
            )
        result = executor.run_until_idle()
        self.assertEqual("completed", result.state)
        self.assertEqual(2001, result.steps)
        self.assertEqual(1, len(result.outputs["sink"]))
        self.assertEqual(1000, executor._memory["counter"]["count"])

    def test_graph_rejects_unknown_ports_and_cycle_guard_is_explicit(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown source port"):
            WorkflowGraph.from_document(workflow_document(
                [node("a", "wf_source", ("out",)), node("b", "wf_sink", ("in",))],
                [edge("bad", "a", "b", "missing")],
            ))
        graph = WorkflowGraph.from_document(workflow_document(
            [node("a", "wf_junction", ("in", "out")), node("b", "wf_junction", ("in", "out"))],
            [edge("ab", "a", "b"), edge("ba", "b", "a")],
        ))
        executor = WorkflowExecutor(graph, clock=lambda: 0.0, max_steps=10)
        executor.enqueue("a", "loop")
        with self.assertRaisesRegex(RuntimeError, "possible infinite cycle"):
            executor.run_until_idle()

    def test_bounded_runtime_queue_exposes_deterministic_backpressure(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [node("source", "wf_source", ("out",))], []
        ))
        executor = WorkflowExecutor(
            graph, clock=lambda: 0.0, max_queue_size=2,
            backpressure_policy="drop_oldest",
        )
        executor.enqueue("source", "a", token_id="a")
        executor.enqueue("source", "b", token_id="b")
        executor.enqueue("source", "c", token_id="c")
        self.assertEqual(2, executor.pressure().queued)
        self.assertEqual(1, executor.pressure().dropped)
        result = executor.run_until_idle()
        self.assertEqual(("b", "c"), result.outputs["source"])
        self.assertIn("token_dropped", [event.event for event in executor.trace()])

        rejecting = WorkflowExecutor(
            graph, clock=lambda: 0.0, max_queue_size=1,
            backpressure_policy="reject_new",
        )
        rejecting.enqueue("source", "first")
        with self.assertRaises(WorkflowBackpressureError):
            rejecting.enqueue("source", "second")
        self.assertEqual(1, rejecting.pressure().rejected)

    def test_queue_component_uses_its_own_capacity_and_overflow_policy(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [
                node("queue", "wf_queue", ("in", "out"), capacity=1, overflow="drop_newest"),
                node("sink", "wf_sink", ("in",)),
            ],
            [edge("queue-sink", "queue", "sink")],
        ))
        executor = WorkflowExecutor(graph, clock=lambda: 0.0, max_queue_size=10)
        executor.enqueue("queue", "first", token_id="first")
        executor.enqueue("queue", "second", token_id="second")
        result = executor.run_until_idle()
        self.assertEqual(("first",), result.outputs["sink"])
        self.assertEqual(1, executor.pressure().dropped)

    def test_recurring_schedule_is_finite_and_logical_time_driven(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [node("timer", "wf_timer", ("in", "out")), node("sink", "wf_sink", ("in",))],
            [edge("timer-sink", "timer", "sink")],
        ))
        executor = WorkflowExecutor(graph, clock=lambda: 0.0)
        schedule_id = executor.schedule_recurring(
            "timer", {"tick": True}, interval=1.0, initial_delay=0.0,
            max_occurrences=3, catch_up="all", schedule_id="ticks",
        )
        self.assertEqual("ticks", schedule_id)
        first = executor.run_until_idle()
        self.assertEqual("waiting", first.state)
        self.assertEqual(1, len(first.outputs["sink"]))
        self.assertEqual("active", executor.schedules()[0].state)
        final = executor.advance(2.5)
        self.assertEqual("completed", final.state)
        self.assertEqual(3, len(final.outputs["sink"]))
        self.assertEqual(3, executor.schedules()[0].emitted)

    def test_latest_and_skip_catch_up_keep_overdue_schedule_bounded(self) -> None:
        graph = WorkflowGraph.from_document(workflow_document(
            [node("timer", "wf_timer", ("in", "out")), node("sink", "wf_sink", ("in",))],
            [edge("timer-sink", "timer", "sink")],
        ))
        latest = WorkflowExecutor(graph, clock=lambda: 0.0)
        latest.schedule_recurring(
            "timer", "latest", interval=1.0, initial_delay=1.0,
            max_occurrences=5, catch_up="latest", schedule_id="latest",
        )
        latest_result = latest.advance(4.2)
        self.assertEqual("waiting", latest_result.state)
        self.assertEqual(("latest",), latest_result.outputs["sink"])
        self.assertEqual(3, latest.schedules()[0].skipped)

        skipped = WorkflowExecutor(graph, clock=lambda: 0.0)
        skipped.schedule_recurring(
            "timer", "skip", interval=1.0, initial_delay=1.0,
            max_occurrences=5, catch_up="skip", schedule_id="skip",
        )
        skipped_result = skipped.advance(4.2)
        self.assertEqual("waiting", skipped_result.state)
        self.assertFalse(skipped_result.outputs.get("sink"))
        self.assertEqual(4, skipped.schedules()[0].skipped)


if __name__ == "__main__":
    unittest.main()
