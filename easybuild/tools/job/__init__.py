##
# Copyright 2015-2015 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""Abstract interface for submitting jobs and related utilities."""


from abc import ABCMeta, abstractmethod

from vsc.utils.missing import get_subclasses

from easybuild.tools.config import get_job_backend
from easybuild.tools.config import PREFERRED_JOB_SERVERS
from easybuild.tools.utilities import import_available_modules


class JobServer(object):
    __metaclass__ = ABCMeta

    USABLE = False

    @abstractmethod
    def begin(self):
        """
        Start a bulk job submission.

        Jobs may be queued and only actually submitted when `commit()`
        is called.
        """
        pass

    @abstractmethod
    def make_job(self, script, name, env_vars=None, hours=None, cores=None):
        """
        Create and return a `Job` object with the given parameters.

        See the `Job`:class: constructor for an explanation of what
        the arguments are.
        """
        pass

    @abstractmethod
    def submit(self, job, after=frozenset()):
        """
        Submit a job to the batch-queueing system.

        If second optional argument `after` is given, it must be a
        sequence of jobs that must be successfully terminated before
        the new job can run.

        Note that actual submission may be delayed until `commit()` is
        called.
        """
        pass

    @abstractmethod
    def commit(self):
        """
        End a bulk job submission.

        Releases any jobs that were possibly queued since the last
        `begin()` call.

        No more job submissions should be attempted after `commit()`
        has been called, until a `begin()` is invoked again.
        """
        pass


def avail_job_servers(check_usable=True):
    """
    Return all known job execution backends.
    """
    import_available_modules('easybuild.tools.job')
    class_dict = dict([(x.__name__, x)
                       for x in get_subclasses(JobServer)
                       if (x.USABLE or not check_usable)])
    return class_dict


def job_server():
    """
    Return interface to job server.
    """
    job_server = get_job_backend()
    job_server_class = avail_job_servers().get(job_server)
    return job_server_class()


def preferred_job_server(order=PREFERRED_JOB_SERVERS):
    """
    Return name of preferred concrete `JobServer` instance, or `None`
    if none is available.
    """
    available_backends = avail_job_servers()
    for backend in order:
        if backend in available_backends:
            return backend
            break
    return None