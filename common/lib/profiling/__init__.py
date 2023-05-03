import functools
import os

import line_profiler

PROFILE_ENABLED = os.environ.get("PYTHON_PROFILE_ENABLE", "").lower() == "true"
PROFILE_LOG_SENT = False


def profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global PROFILE_ENABLED
        global PROFILE_LOG_SENT
        if PROFILE_ENABLED:
            if not PROFILE_LOG_SENT:
                print(
                    "Profiling enabled. This will print time statistics about the profiled "
                    "functions, but it will prevent your debugger from working."
                )
                PROFILE_LOG_SENT = True
            profiler = line_profiler.LineProfiler()
            profiler.add_function(func)
            profiler.enable_by_count()

        result = func(*args, **kwargs)

        if PROFILE_ENABLED:
            profiler.disable_by_count()
            profiler.print_stats()

        return result

    return wrapper


def async_profile(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        global PROFILE_ENABLED
        global PROFILE_LOG_SENT
        if PROFILE_ENABLED:
            if not PROFILE_LOG_SENT:
                print(
                    "Profiling enabled. This will print time statistics about the profiled "
                    "functions, but it will prevent your debugger from working."
                )
                PROFILE_LOG_SENT = True
            profiler = line_profiler.LineProfiler()
            profiler.add_function(func)
            profiler.enable_by_count()

        result = await func(*args, **kwargs)

        if PROFILE_ENABLED:
            profiler.disable_by_count()
            profiler.print_stats()

        return result

    return wrapper
