import os
import sys

from django.core.management.base import BaseCommand
from redis.exceptions import ConnectionError
from rq.logutils import setup_loghandlers

from django_rq.utils import configure_sentry, reset_db_connections
from django_rq.workers import get_worker


class Command(BaseCommand):
    """
    Compatibility wrapper for django-rq on newer rq releases where
    `rq.Connection` is no longer exported.
    """

    args = "<queue queue ...>"

    def add_arguments(self, parser):
        parser.add_argument("--worker-class", action="store", dest="worker_class", help="RQ Worker class to use")
        parser.add_argument("--pid", action="store", dest="pid", default=None, help="PID file path")
        parser.add_argument("--burst", action="store_true", dest="burst", default=False, help="Run worker in burst mode")
        parser.add_argument(
            "--with-scheduler",
            action="store_true",
            dest="with_scheduler",
            default=False,
            help="Run worker with scheduler enabled",
        )
        parser.add_argument("--name", action="store", dest="name", default=None, help="Worker name")
        parser.add_argument("--queue-class", action="store", dest="queue_class", help="Queue class to use")
        parser.add_argument("--job-class", action="store", dest="job_class", help="Job class to use")
        parser.add_argument("--worker-ttl", action="store", type=int, dest="worker_ttl", default=420)
        parser.add_argument("--sentry-dsn", action="store", default=None, dest="sentry_dsn")
        parser.add_argument("--sentry-ca-certs", action="store", default=None, dest="sentry_ca_certs")
        parser.add_argument("--sentry-debug", action="store", default=False, dest="sentry_debug")
        parser.add_argument("--max-jobs", action="store", default=None, dest="max_jobs", type=int)
        parser.add_argument(
            "--serializer",
            action="store",
            default="rq.serializers.DefaultSerializer",
            dest="serializer",
            help="Custom serializer import path",
        )
        parser.add_argument("args", nargs="*", type=str, help="Queues to work on")

    def handle(self, *args, **options):
        pid = options.get("pid")
        if pid:
            with open(os.path.expanduser(pid), "w", encoding="utf-8") as fp:
                fp.write(str(os.getpid()))

        verbosity = options.get("verbosity")
        if verbosity >= 2:
            level = "DEBUG"
        elif verbosity == 0:
            level = "WARNING"
        else:
            level = "INFO"
        setup_loghandlers(level)

        sentry_dsn = options.pop("sentry_dsn")
        if sentry_dsn:
            try:
                configure_sentry(sentry_dsn, **options)
            except ImportError:
                self.stderr.write("Please install sentry-sdk using `pip install sentry-sdk`")
                sys.exit(1)

        try:
            worker_kwargs = {
                "worker_class": options["worker_class"],
                "queue_class": options["queue_class"],
                "job_class": options["job_class"],
                "name": options["name"],
                "default_worker_ttl": options["worker_ttl"],
                "serializer": options["serializer"],
            }
            worker = get_worker(*args, **worker_kwargs)
            reset_db_connections()
            worker.work(
                burst=options.get("burst", False),
                with_scheduler=options.get("with_scheduler", False),
                logging_level=level,
                max_jobs=options["max_jobs"],
            )
        except ConnectionError as exc:
            self.stderr.write(str(exc))
            sys.exit(1)
