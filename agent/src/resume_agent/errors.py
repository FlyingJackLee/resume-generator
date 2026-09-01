class ResumeAgentError(RuntimeError):
    """A safe, user-facing resume compiler error."""


class PatchError(ResumeAgentError):
    """A patch is malformed or targets protected resume data."""

