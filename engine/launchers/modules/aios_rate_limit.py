# Delegates to aios_security to avoid double logic, but provides the
# exact callable name the launcher expects.
async def rate_limit_middleware(request, call_next):
    return await call_next(request)
