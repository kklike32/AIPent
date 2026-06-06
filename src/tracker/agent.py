from __future__ import annotations


class ActionAgent:
    """
    Future: executes approved actions on behalf of the user.

    Must require explicit user confirmation before taking actions.
    """

    # TODO: Add explicit approval workflow before any action execution.
    def run(self) -> None:
        raise NotImplementedError("ActionAgent is a future placeholder.")
