"""Refactored, minimal Streamlit entrypoint demonstrating SRP and DI.

This file is intentionally small: it shows how the UI depends on
focused service classes rather than many independent functions.
"""
import streamlit as st
from AgentOrchestration.services import AuthService, MetricsService, RecoveryService


def main(auth: AuthService, metrics: MetricsService, recovery: RecoveryService):
    st.title("Refactored Blog Agent (Demo)")

    try:
        auth.login()
    except Exception:
        st.warning("Login required; using limited demo mode")

    st.header("Metrics")
    try:
        m = metrics.get_metrics()
        st.metric("Total Requests", m.get('total_requests', 0))
        st.metric("Success Rate", f"{m.get('generation_success_rate', 0)}%")
    except Exception as e:
        st.error(f"Metrics unavailable: {e}")

    st.header("Recovery")
    try:
        cps = recovery.get_checkpoints()
        if cps:
            selected = st.selectbox("Checkpoint", cps)
            if st.button("Recover"):
                r = recovery.recover(selected)
                st.write(r)
        else:
            st.info("No checkpoints available")
    except Exception as e:
        st.error(f"Recovery error: {e}")


if __name__ == '__main__':
    auth = AuthService()
    metrics = MetricsService()
    recovery = RecoveryService()
    main(auth, metrics, recovery)
