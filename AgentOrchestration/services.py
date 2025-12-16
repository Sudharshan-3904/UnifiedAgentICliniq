"""Lightweight service adapters to improve separation of concerns.

These adapters wrap the procedural functions in `blog_agent` and provide
single-responsibility classes so the UI code depends on small focused
abstractions rather than many independent functions.
"""
from typing import Any, Dict, List
import blog_agent


class AuthService:
    def login(self) -> None:
        return blog_agent.login()


class MetricsService:
    def get_metrics(self) -> Dict[str, Any]:
        return blog_agent.get_metrics()


class ChaosService:
    def enable(self, rate: float) -> Any:
        return blog_agent.enable_chaos_testing(rate)

    def disable(self) -> Any:
        return blog_agent.disable_chaos_testing()

    def get_metrics(self) -> Dict[str, Any]:
        return blog_agent.get_chaos_metrics()

    def reset_metrics(self) -> Any:
        return blog_agent.reset_chaos_metrics()


class RecoveryService:
    def get_checkpoints(self) -> List[str]:
        return blog_agent.get_checkpoints()

    def recover(self, checkpoint: str) -> Dict[str, Any]:
        return blog_agent.recover_from_checkpoint(checkpoint)

    def clear(self) -> Dict[str, Any]:
        return blog_agent.clear_checkpoints()


class DebugService:
    def get_debug_logs(self) -> List[Dict[str, Any]]:
        return blog_agent.get_debug_logs()

    def clear_debug_logs(self) -> None:
        return blog_agent.clear_debug_logs()

    def get_masked_key(self) -> str:
        return blog_agent.get_masked_langsmith_key()

    def save_event(self, event: Dict[str, Any]) -> Any:
        return blog_agent.save_event_to_langsmith(event)
