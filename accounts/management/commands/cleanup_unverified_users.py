"""Hapus akun belum verifikasi yang sudah melewati batas waktu."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Hapus user inactive dan belum verifikasi yang sudah kedaluwarsa."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Tampilkan user yang akan dihapus tanpa menghapus data.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=settings.UNVERIFIED_USER_CLEANUP_DAYS,
            help="Override cutoff dalam hari. Default dari settings.",
        )
        parser.add_argument(
            "--no-confirm",
            action="store_true",
            help="Lewati prompt konfirmasi sebelum hapus.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Jumlah user per batch. Default 100.",
        )

    def handle(self, *args, **options) -> None:
        days = options["days"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        no_confirm = options["no_confirm"]

        if days < 0:
            raise CommandError("--days tidak boleh negatif.")
        if batch_size <= 0:
            raise CommandError("--batch-size harus lebih besar dari 0.")

        cutoff = timezone.now() - timedelta(days=days)
        user_model = get_user_model()
        stale_users = user_model.objects.filter(
            is_active=False,
            profile__email_verified=False,
            date_joined__lt=cutoff,
        ).order_by("date_joined", "pk")

        total = stale_users.count()
        self.stdout.write(
            f"Cutoff: {cutoff.isoformat()} | kandidat: {total} | dry_run={dry_run} | batch_size={batch_size}"
        )

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Tidak ada user stale."))
            return

        if not dry_run and not no_confirm:
            confirm = input(f"Hapus {total} user stale? ketik 'yes' untuk lanjut: ").strip().lower()
            if confirm != "yes":
                self.stdout.write(self.style.WARNING("Batal."))
                return

        processed_total = 0
        last_pk = 0
        while True:
            batch = list(
                stale_users.filter(pk__gt=last_pk).values_list("pk", "email", "date_joined")[:batch_size]
            )
            if not batch:
                break
            last_pk = batch[-1][0]

            for _, email, date_joined in batch:
                line = f"{email} | joined={date_joined.isoformat()}"
                logger.info("cleanup_unverified_users candidate: %s", line)
                self.stdout.write(line)

            if not dry_run:
                with transaction.atomic():
                    user_model.objects.filter(pk__in=[pk for pk, _, _ in batch]).delete()

            processed_total += len(batch)

        action = "akan dihapus" if dry_run else "dihapus"
        self.stdout.write(self.style.SUCCESS(f"Selesai. {processed_total} user {action}."))
