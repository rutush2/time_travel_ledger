from typing import Any, Dict, List, Optional
from schema import EventEnvelope


def apply_event_mutation(state: Dict[str, Any], event: EventEnvelope) -> Dict[str, Any]:
    new_state = dict(state)
    event_type = event.event_type.upper()
    payload = event.payload

    if event_type == "PROVISION_NODE":
        new_state["hostname"] = payload.get("hostname", "unknown-node")
        new_state["cpu_cores"] = payload.get("cpu_cores", 8)
        new_state["memory_gb"] = payload.get("memory_gb", 32)
        new_state["status"] = "RUNNING"
        new_state["active_pods"] = 0

    elif event_type == "DEPLOY_POD":
        pods = payload.get("pod_count", 1)
        new_state["active_pods"] = new_state.get("active_pods", 0) + pods

    elif event_type == "TERMINATE_POD":
        pods = payload.get("pod_count", 1)
        new_state["active_pods"] = max(0, new_state.get("active_pods", 0) - pods)

    elif event_type == "ISOLATE_SUBNET":
        new_state["status"] = "ISOLATED"
        new_state["isolation_reason"] = payload.get("reason", "manual_override")

    else:
        for key, value in payload.items():
            new_state[key] = value

    return new_state


def project_state(
    initial_state: Optional[Dict[str, Any]],
    events: List[EventEnvelope]
) -> Dict[str, Any]:

    current_state = dict(initial_state) if initial_state is not None else {}

    for event in events:
        current_state = apply_event_mutation(current_state, event)

    return current_state