#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2023
#
# Author(s):
#
#   Trygve Aspenes <trygveas@met.no>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import fcntl
import json
import logging
from pathlib import Path
from typing import Any, Tuple

import re
import base64
import datetime

from pygeoapi.process.base import BaseProcessor
from pygeoapi.process.manager.base import BaseManager
from pygeoapi.util import JobStatus

from celery import Celery
from celery.result import AsyncResult

import redis

null = None
status = {'SUCCESS': 'successful',
          'STARTED': 'running',
          'PENDING': 'dismissed'}

LOGGER = logging.getLogger(__name__)


class celery_redis_manager(BaseManager):
    """generic Manager ABC"""

    def __init__(self, manager_def: dict):
        """
        Initialize object

        :param manager_def: manager definition

        :returns: `pygeoapi.process.manager.base.BaseManager`
        """

        super().__init__(manager_def)
        self.is_async = True
        self.results = {}

        self.broker = manager_def.get('broker', 'redis://')
        self.backend = manager_def.get('backend', 'redis://')
        self.result_backend = manager_def.get('result_backend', 'redis://')
        self.app = Celery('proj',
                          broker=self.broker,
                          backend=self.backend,
                          result_backend=self.result_backend)
        # self.app.conf.update(results_expires=30,)
        # print("CELRY CONFIG", self.app.conf)

    def delete_job(self, job_id: str) -> bool:
        """
        Deletes a job

        :param job_id: job identifier

        :return `bool` of status result
        """

        res = AsyncResult(job_id,app=self.app).revoke(terminate=True)
        return True

    def get_jobs(self, status: JobStatus = None) -> list:
        """
        Get process jobs, optionally filtered by status

        :param status: job status (accepted, running, successful,
                       failed, results) (default is all)

        :returns: `list` of jobs (identifier, status, process identifier)
        """

        _jobs = []
        i = self.app.control.inspect()
        print("JOBS", i.active())
        print("JOBS", i.scheduled())
        print("JOBS", i.registered())
        print("JOBS", i.reserved())
        print("QUEUES", i.query_task('*'))
        redis_cache = redis.Redis()
        redis_job_ids = redis_cache.keys('celery-task-meta-*')
        for redis_job_id in redis_job_ids:
            print(redis_job_id.decode('utf-8'))
            z = re.match('celery-task-meta-(.*)', redis_job_id.decode('utf-8'))
            if z:
                print("GROUPS", z.groups(1)[0])
                _jobs.append({"identifier": z.groups(1)[0], 'process_id': '', 'job_start_datetime':'',
                              'job_end_datetime':'', 'status': 'successful', 'location': None, 'mimetype': None,
                              'message': 'ANy message', 'progress': 0})
        #{'identifier': '0d0f7d8e-9b1b-11ed-80c4-e884a5ddae7d', 'process_id': 'process-netcdf',
        # 'job_start_datetime': '2023-01-23T12:40:00.389709Z', 'job_end_datetime': '2023-01-23T12:40:00.392050Z',
        # 'status': 'failed', 'location': None, 'mimetype': None, 'message': 'InvalidParameterValue: Error updating job', 'progress': 5}
        return _jobs

    def get_job(self, job_id: str) -> dict:
        """
        Get a single job

        :param job_id: job identifier

        :returns: `dict`  # `pygeoapi.process.manager.Job`
        """
        res = AsyncResult(job_id,app=self.app)


        print("QUERY_TASL", self.app.control.inspect().query_task(job_id))
        #print(res.query_task(job_id))
        print(dir(res))
        print("RESULTS state", res.state)
        print("RESULTS status",  res.status)
        result = {'task_id': job_id,
                  'name': res.name,
                  'status': res.status}

        return {'identifier': result.get('task_id', job_id), 'process_id': result.get('name', 'Unknown'), 'job_start_datetime': '',
                'job_end_datetime': result.get('date_done',''), 'status': status.get(result.get('status','running')),
                'location': 'Dummy', 'mimetype': None, 'message': '', 'progress': 'Not Set'}


    def get_job_result(self, job_id: str) -> Tuple[str, Any]:
        """
        Get a job's status, and actual output of executing the process

        :param jobid: job identifier

        :returns: `tuple` of mimetype and raw output
        """

        redis_cache = redis.Redis()
        redis_job_id = redis_cache.keys('*' + job_id)[0].decode('utf-8')
        job_result = eval(redis_cache.get(redis_job_id).decode('utf-8'))

        res = AsyncResult(job_id,app=self.app)
        print("RESULTS", res)
        if res.ready():
            print("Results are ready")
            _result = res.result
            if isinstance(_result, list):
                try:
                    mimetype = _result[0]
                    encoded_result = base64.b64decode(_result[1])
                except:
                    print("Failed to get result")
                    return (None,)
        else:
            print("Results are NOT ready")
            return (None,)
            
        return mimetype, encoded_result

    def execute_process(self, p: BaseProcessor, job_id: str, data_dict: dict,
                        is_async: bool = False) -> Tuple[str, Any, int]:
        """
        Default process execution handler

        :param p: `pygeoapi.process` object
        :param job_id: job identifier
        :param data_dict: `dict` of data parameters
        :param is_async: `bool` specifying sync or async processing.

        :returns: tuple of MIME type, response payload and status
        """

        jfmt = 'application/json'

        print("PPPPPP", p, is_async, job_id)
        print(datetime.datetime.now())
        result = p.execute.apply_async((data_dict, data_dict), task_id=job_id)
        #result = p.execute(data_dict, job_id)
        #p.state(data_dict)
        self.results[result.id] = result
        print(datetime.datetime.now())
        print("After delay", result)
        print("After delay", result.id)
        print("After delay", result.info)
        print("After delay", result.state)
        print("After delay", result.status)

        # if is_async:
        #     LOGGER.debug('Dummy manager does not support asynchronous')
        #     LOGGER.debug('Forcing synchronous execution')

        jfmt = "heu"
        outputs = "nhe"
        try:
            print("DATA DICTS", data_dict)
            #jfmt, outputs = p.execute(data_dict)
            current_status = JobStatus.successful
        except Exception as err:
            outputs = {
                'code': 'InvalidParameterValue',
                'description': 'Error updating job'
            }
            current_status = JobStatus.failed
            LOGGER.exception(err)
            LOGGER.error(err)

        #return jfmt, outputs, current_status
        return 'application/json', None, JobStatus.accepted

    def __repr__(self):
        return f'<my_own_manager> {self.name}'
