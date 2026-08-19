import json
import sqlite3
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

import config

API_BASE_URL = f"http://{config.HOST}:{config.PORT}"

st.set_page_config(
    page_title="Time-Travel Ledger C2 Center",
    page_icon="⏳",
    layout="wide"
)

st.title("⏳ Replay-Driven Audit & Time-Travel Ledger")
st.caption(
    "Immutable Event Store • Deterministic State Replay • Retroactive Divergence Analysis • Forensic Chain Repair")

st.sidebar.header("🕹️ System Controls")

if st.sidebar.button("🔍 Verify Cryptographic Integrity"):
    try:
        res = requests.get(f"{API_BASE_URL}/api/integrity/check")
        if res.status_code == 200:
            data = res.json()
            if data.get("integrity_valid"):
                st.sidebar.success("✅ Hash Chain Intact (SHA-256 Valid)")
            else:
                st.sidebar.error("❌ HASH CHAIN CORRUPTED!")
    except Exception as e:
        st.sidebar.error(f"Failed to connect to API server: {e}")

st.sidebar.markdown("---")

tab_replay, tab_append, tab_inject, tab_analytics, tab_forensics = st.tabs([
    "⏱️ Time-Travel Replay",
    "➕ Append Event",
    "🔀 Retroactive Injection",
    "📊 Ledger Analytics",
    "🕵️ Forensic Audit & Repair"
])


def fetch_raw_events():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY sequence_id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


with tab_replay:
    st.subheader("Point-in-Time State Reconstruction")

    col_input1, col_input2 = st.columns(2)
    with col_input1:
        agg_type = st.text_input("Aggregate Type", value="cluster_node", key="replay_agg_type")
    with col_input2:
        agg_id = st.text_input("Aggregate ID", value="node-eu-west-04", key="replay_agg_id")

    raw_events = fetch_raw_events()
    max_seq = len(raw_events)

    if max_seq > 1:
        target_seq = st.slider(
            "Select Sequence ID to Reconstruct State At:",
            min_value=1,
            max_value=max_seq,
            value=max_seq
        )

        if st.button("🚀 Reconstruct State"):
            res = requests.get(
                f"{API_BASE_URL}/api/state/{agg_type}/{agg_id}",
                params={"at_sequence_id": target_seq}
            )
            if res.status_code == 200:
                state_data = res.json()

                c1, c2, c3 = st.columns(3)
                c1.metric("Sequence ID", state_data["sequence_id"])
                c2.metric("Events Replayed", state_data["events_replayed"])
                c3.metric("Timestamp", state_data["timestamp"][:19])

                st.subheader("State Snapshot at Selected Sequence")
                st.json(state_data["state"])
            else:
                st.error("Failed to retrieve state baseline.")
    elif max_seq == 1:
        target_seq = 1
        st.info("Only 1 event exists in the ledger.")
        if st.button("🚀 Reconstruct State"):
            res = requests.get(
                f"{API_BASE_URL}/api/state/{agg_type}/{agg_id}",
                params={"at_sequence_id": target_seq}
            )
            if res.status_code == 200:
                state_data = res.json()

                c1, c2, c3 = st.columns(3)
                c1.metric("Sequence ID", state_data["sequence_id"])
                c2.metric("Events Replayed", state_data["events_replayed"])
                c3.metric("Timestamp", state_data["timestamp"][:19])

                st.subheader("State Snapshot at Selected Sequence")
                st.json(state_data["state"])
            else:
                st.error("Failed to retrieve state baseline.")
    else:
        st.info("No events recorded in the ledger yet. Append events to enable time travel.")

with tab_append:
    st.subheader("Append Atomic Mutation Event")

    with st.form("append_event_form"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            app_agg_type = st.text_input("Aggregate Type", value="cluster_node")
        with col_b:
            app_agg_id = st.text_input("Aggregate ID", value="node-eu-west-04")
        with col_c:
            app_event_type = st.selectbox(
                "Event Type",
                ["PROVISION_NODE", "DEPLOY_POD", "TERMINATE_POD", "ISOLATE_SUBNET", "UNFREEZE_NODE"]
            )

        payload_str = st.text_area("Payload (JSON)",
                                   value='{"hostname": "worker-04", "cpu_cores": 16, "memory_gb": 64}')
        submit_append = st.form_submit_button("📥 Publish Event to Ledger")

        if submit_append:
            try:
                payload_dict = json.loads(payload_str)
                res = requests.post(f"{API_BASE_URL}/api/events", json={
                    "aggregate_type": app_agg_type,
                    "aggregate_id": app_agg_id,
                    "event_type": app_event_type,
                    "payload": payload_dict
                })
                if res.status_code == 201:
                    st.success("Event appended successfully!")
                    st.rerun()
                else:
                    st.error(f"Error appending event: {res.text}")
            except Exception as e:
                st.error(f"Invalid JSON payload: {e}")

with tab_inject:
    st.subheader("Retroactive Event Injection & State Divergence Engine")
    st.warning("Injecting an event into the past invalidates subsequent snapshots and recalculates state timelines.")

    with st.form("inject_event_form"):
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            inj_agg_type = st.text_input("Aggregate Type", value="cluster_node", key="inj_type")
            inj_agg_id = st.text_input("Aggregate ID", value="node-eu-west-04", key="inj_id")
        with col_i2:
            inj_event_type = st.selectbox("Event Type", ["PROVISION_NODE", "ISOLATE_SUBNET", "TERMINATE_POD"],
                                          key="inj_evt")
            inj_timestamp = st.text_input("Retroactive ISO Timestamp", value="2026-08-16T12:00:00Z")

        inj_payload_str = st.text_area("Payload (JSON)", value='{"reason": "security_quarantine"}', key="inj_payload")
        submit_inject = st.form_submit_button("🔀 Execute Retroactive Injection")

        if submit_inject:
            try:
                payload_dict = json.loads(inj_payload_str)
                res = requests.post(f"{API_BASE_URL}/api/inject-retroactive", json={
                    "aggregate_type": inj_agg_type,
                    "aggregate_id": inj_agg_id,
                    "retroactive_timestamp": inj_timestamp,
                    "event_type": inj_event_type,
                    "payload": payload_dict
                })
                if res.status_code == 200:
                    data = res.json()
                    st.success("Retroactive Injection Complete!")

                    divergence = data["divergence_delta"]
                    st.subheader("Divergence Delta Analysis")

                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.markdown("**Original Head State**")
                        st.json(divergence["original_state"])
                    with col_d2:
                        st.markdown("**Recalculated Head State**")
                        st.json(divergence["recalculated_state"])
                else:
                    st.error(f"Injection Failed: {res.text}")
            except Exception as e:
                st.error(f"Invalid Input: {e}")

with tab_analytics:
    st.subheader("Raw Ledger Event Stream & Chain Integrity")
    events = fetch_raw_events()

    if events:
        df = pd.DataFrame(events)
        st.dataframe(
            df[["sequence_id", "timestamp", "aggregate_type", "aggregate_id", "event_type", "prev_hash", "hash"]],
            use_container_width=True)

        fig = px.bar(
            df,
            x="sequence_id",
            y="sequence_id",
            color="event_type",
            title="Event Sequence Growth by Type",
            labels={"sequence_id": "Sequence ID"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No records in event ledger.")

with tab_forensics:
    st.subheader("🌐 Forensic Ledger Audit & Cryptographic Repair")

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        st.markdown("### 🔍 Forensic Inspection")
        if st.button("Run Forensic Chain Audit"):
            res = requests.get(f"{API_BASE_URL}/api/forensics/audit")
            if res.status_code == 200:
                report = res.json()
                if report["is_chain_valid"]:
                    st.success(
                        f"✅ All {report['total_events_scanned']} events cryptographically verified. No tampering detected.")
                else:
                    st.error(f"❌ Corruption Detected at Sequence ID: {report['first_corrupted_sequence_id']}")
                    st.json(report)
            else:
                st.error(f"Audit request failed: {res.text}")

        st.markdown("---")
        st.markdown("### 🛠️ Cryptographic Re-Sealing")
        repair_seq = st.number_input("Start Repair from Sequence ID", min_value=1, value=1)
        if st.button("Execute Chain Re-Sealing"):
            res = requests.post(f"{API_BASE_URL}/api/forensics/repair", json={"start_sequence_id": repair_seq})
            if res.status_code == 200:
                st.success(f"Chain re-sealed successfully: {res.json()}")
                st.rerun()
            else:
                st.error(f"Repair failed: {res.text}")

    with col_f2:
        st.markdown("### 🧪 Simulate Database Tampering")
        st.caption(
            "Tamper with an event payload directly in SQLite without updating its SHA-256 hash to test detection.")

        raw_evts = fetch_raw_events()
        if raw_evts:
            tamper_seq = st.number_input("Sequence ID to Tamper", min_value=1, max_value=len(raw_evts), value=1)
            tamper_payload_str = st.text_area("Corrupted Payload (JSON)",
                                              value='{"hostname": "HACKED_NODE", "unauthorized_access": true}')

            if st.button("⚠️ Tamper Event Data"):
                try:
                    payload_dict = json.loads(tamper_payload_str)
                    res = requests.post(f"{API_BASE_URL}/api/forensics/simulate-tamper", json={
                        "sequence_id": tamper_seq,
                        "corrupted_payload": payload_dict
                    })
                    if res.status_code == 200:
                        st.warning(
                            f"Event sequence {tamper_seq} payload modified in database! Run audit to test detection.")
                    else:
                        st.error(f"Tamper failed: {res.text}")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")
        else:
            st.info("No events available to tamper with yet.")