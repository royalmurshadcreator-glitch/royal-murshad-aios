"""Publish the validated server-side identity to downstream middleware."""


async def session_identity_middleware(request, call_next):
    identity = getattr(request.state, "auth_identity", None)
    request.state.user = identity
    request.state.user_id = identity.get("id") if isinstance(identity, dict) else None
    request.state.username = identity.get("username") if isinstance(identity, dict) else None
    request.state.role = identity.get("role") if isinstance(identity, dict) else None
    return await call_next(request)
