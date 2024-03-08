from . import mux
import schedule
from functools import partial
import luigi

TASKS = [
    [schedule.every(5).minutes, mux.BUILD_KWARGS],
]


for idx, (table, kwargs) in enumerate(TASKS):
    TASKS[idx] = [table, partial(luigi.build, **kwargs)]