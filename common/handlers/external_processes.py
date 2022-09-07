import subprocess
from collections import defaultdict

from common.config import config

logger = config.get_logger()

# SINGLETON: on purpose (we only want one)
tracked_procs = defaultdict(dict)


def launch_proc(name, cmd, env=None, cwd=None):
    if name in tracked_procs:
        raise ValueError(f"Process {name} already running")
    if isinstance(cmd, str):
        cmd = cmd.split()
    elif not isinstance(cmd, list):
        raise ValueError(f"cmd must be a string or list, not {type(cmd)}")
    logger.info(f"Launching {name} with command {cmd}")
    proc = subprocess.Popen(cmd, env=env, cwd=cwd)
    logger.info(f"Launched {name} with pid {proc.pid}")
    tracked_procs[name] = {"proc": proc}


def kill_proc(name):
    if name not in tracked_procs:
        raise ValueError(f"Process {name} not running")
    logger.info(f"Killing {name} with pid {tracked_procs[name]['proc'].pid}")
    tracked_procs[name]["proc"].kill()
    del tracked_procs[name]
