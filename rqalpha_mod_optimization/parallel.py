# -*- coding: utf-8 -*-
# __author__ = "Morrison"
import multiprocessing
from itertools import chain

import concurrent.futures
import dask.multiprocessing
import enum
from dask import delayed, compute


def run_synchronize(func, tasks, *args, **kwargs):
    results = []
    for task in tasks:
        results.append(func(task, *args, **kwargs))
    return results


def run_multiprocess(func, tasks, *args, **kwargs):
    results = []
    remains = list(enumerate(tasks))
    while remains:
        errors = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            futures = [executor.submit(func, *tuple(chain([task], args)), **kwargs) for _, task in remains]
            concurrent.futures.wait(futures)
            for future, t in zip(futures, remains):
                n, task = t
                try:
                    results.append((n, future.result()))
                except Exception as e:
                    errors.append((n, task))
        remains = errors
    return list(map(lambda x: x[1], sorted(results, key=lambda x: x[0])))


def run_raw_multiprocess(func, tasks, *args, **kwargs):
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count(), maxtasksperchild=1)
    futures = []
    for task in tasks:
        futures.append(pool.apply_async(func, tuple(chain([task], args)), kwargs))
    pool.close()
    results = list(map(lambda x: x.get(), futures))
    return results


def run_dask_multiprocess(func, tasks, *args, **kwargs):
    all_delayed = [delayed(func)(task, *args, **kwargs) for task in tasks]
    results = list(compute(*all_delayed, get=dask.multiprocessing.get))
    return results


class ParallelMethod(enum.Enum):
    NONE = "NONE",
    PROCESS = "PROCESS"
    PROCESS_RAW = "PROCESS_RAW"
    DASK = "DASK"


_run_parallel_method = ParallelMethod.DASK

_PARALLEL_METHOD = {
    ParallelMethod.NONE: run_synchronize,
    ParallelMethod.PROCESS: run_multiprocess,
    ParallelMethod.PROCESS_RAW: run_raw_multiprocess,
    ParallelMethod.DASK: run_dask_multiprocess,
}


def set_parallel_method(value):
    global _run_parallel_method
    value = ParallelMethod(value)
    _run_parallel_method = value


def run_parallel(func, tasks, *args, **kwargs):
    method = _PARALLEL_METHOD.get(_run_parallel_method, run_synchronize)
    return method(func, tasks, *args, **kwargs)
