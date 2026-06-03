import { ACTION_META } from "./constants.js";
import {
  createGenerateJob,
  deleteGenerateJob,
  fetchGenerateJob,
  fetchGenerateJobs,
} from "./api.js";
import {
  renderJobCard,
  renderResultBody,
  setGenerateButtonsLoading,
} from "./render.js";

const POLL_MS = 2000;
const TERMINAL = new Set(["success", "failed"]);

function showToast(message, type = "error") {
  if (window.ToastManager?.[type]) {
    window.ToastManager[type](message);
    return;
  }
  if (window.showToast) {
    window.showToast(message, type);
  }
}

function getReadySourceIds() {
  const selected = window.WorkspaceSelection?.getSelectedSourceIds?.() || [];
  if (selected.length > 0) return selected;

  return Array.from(document.querySelectorAll("[data-source-item]"))
    .filter((item) => item.dataset.sourceReady !== "false")
    .map((item) => item.dataset.sourceId)
    .filter(Boolean);
}

class WorkspaceGenerate {
  constructor(workspaceId) {
    this.workspaceId = workspaceId;
    this.pollIntervals = new Map();
    this.jobsById = new Map();
    this.listEl = document.querySelector("[data-generate-job-list]");
    this.emptyEl = document.querySelector("[data-generate-empty]");
    this.buttons = Array.from(document.querySelectorAll("[data-generate-action]"));
    this.modal = document.getElementById("generate-result-modal");
    this.modalBody = document.getElementById("generate-result-body");
    this.modalTitle = document.getElementById("generate-result-title");
    this.modalSubtitle = document.getElementById("generate-result-subtitle");
    this.btnCopy = document.getElementById("btn-copy-generate-result");
    this.activeJobId = null;
  }

  init() {
    if (!this.listEl) return;

    this.buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const action = btn.dataset.generateAction;
        if (action) this.startGenerate(action);
      });
    });

    this.listEl.addEventListener("click", (event) => {
      const card = event.target.closest("[data-generate-job-id]");
      if (!card) return;
      const jobId = card.dataset.generateJobId;
      const job = this.jobsById.get(jobId);
      if (job) this.openJob(job);
    });

    const closeModal = () => this.closeModal();
    document.getElementById("btn-close-generate-modal")?.addEventListener("click", closeModal);
    document.getElementById("btn-close-generate-modal-footer")?.addEventListener("click", closeModal);
    document.getElementById("generate-result-backdrop")?.addEventListener("click", () => {
      this.closeModal();
    });
    document.getElementById("btn-delete-generate-job")?.addEventListener("click", () => {
      this.deleteActiveJob();
    });
    if (this.btnCopy) {
      this.btnCopy.addEventListener("click", () => {
        if (!this.activeJobId) return;
        const job = this.jobsById.get(this.activeJobId);
        if (job && job.result) {
          navigator.clipboard.writeText(job.result).then(() => {
            const icon = this.btnCopy.querySelector("iconify-icon");
            const textSpan = this.btnCopy.querySelector("span");
            if (icon) {
              icon.setAttribute("icon", "tabler:check");
              icon.classList.add("text-green-400");
            }
            if (textSpan) {
              textSpan.textContent = "Tersalin";
            }
            setTimeout(() => {
              if (icon) {
                icon.setAttribute("icon", "tabler:copy");
                icon.classList.remove("text-green-400");
              }
              if (textSpan) {
                textSpan.textContent = "Salin";
              }
            }, 2000);
            showToast("Hasil generate berhasil disalin ke clipboard.", "success");
          }).catch((err) => {
            console.error("Gagal menyalin hasil generate:", err);
          });
        }
      });
    }

    this.loadJobs();
  }

  async loadJobs() {
    try {
      const data = await fetchGenerateJobs(this.workspaceId);
      const jobs = data.results || [];
      this.renderJobList(jobs);
      jobs
        .filter((job) => !TERMINAL.has(job.status))
        .forEach((job) => this.startPolling(job.id));
    } catch (err) {
      console.error("Gagal memuat daftar generate:", err);
    }
  }

  renderJobList(jobs) {
    this.jobsById.clear();
    this.listEl.querySelectorAll("[data-generate-job-id]").forEach((el) => el.remove());

    jobs.forEach((job) => {
      this.jobsById.set(job.id, job);
      this.listEl.appendChild(renderJobCard(job));
    });

    if (this.emptyEl) {
      this.emptyEl.classList.toggle("hidden", jobs.length > 0);
    }
  }

  upsertJob(job) {
    this.jobsById.set(job.id, job);
    const existing = this.listEl.querySelector(`[data-generate-job-id="${job.id}"]`);
    const card = renderJobCard(job);
    if (existing) {
      existing.replaceWith(card);
    } else {
      this.listEl.prepend(card);
    }
    if (this.emptyEl) {
      this.emptyEl.classList.add("hidden");
    }
    if (this.activeJobId === job.id && this.modal && !this.modal.classList.contains("hidden")) {
      this.openJob(job);
    }
  }

  async startGenerate(action) {
    const sourceIds = getReadySourceIds();
    if (sourceIds.length === 0) {
      showToast("Pilih minimal satu sumber yang siap, atau tunggu proses selesai.", "warning");
      return;
    }

    setGenerateButtonsLoading(this.buttons, action, true);

    try {
      const payload = { action, source_ids: sourceIds };
      if (action === "quiz") {
        payload.options = { question_count: "medium", difficulty: "medium" };
      }

      const data = await createGenerateJob(this.workspaceId, payload);
      const job = data.generate_job;
      if (!job?.id) throw new Error("Respons generate tidak valid.");

      const fullJob = {
        ...job,
        source_ids: sourceIds,
        result: "",
        error_message: "",
      };
      this.upsertJob(fullJob);
      this.startPolling(job.id);
      document.dispatchEvent(new CustomEvent('quotaUsed'));
      showToast(`${ACTION_META[action]?.label || action} dimulai.`, "success");
    } catch (err) {
      showToast(err.message || "Gagal memulai generate.", "error");
    } finally {
      setGenerateButtonsLoading(this.buttons, action, false);
    }
  }

  startPolling(jobId) {
    if (this.pollIntervals.has(jobId)) return;

    const tick = async () => {
      try {
        const job = await fetchGenerateJob(jobId);
        this.upsertJob(job);
        if (TERMINAL.has(job.status)) {
          this.stopPolling(jobId);
          if (job.status === "failed") {
            showToast(job.error_message || "Generate gagal.", "error");
          }
        }
      } catch (err) {
        console.error(`Poll generate gagal (${jobId}):`, err);
      }
    };

    tick();
    const intervalId = setInterval(tick, POLL_MS);
    this.pollIntervals.set(jobId, intervalId);
  }

  stopPolling(jobId) {
    const intervalId = this.pollIntervals.get(jobId);
    if (intervalId) {
      clearInterval(intervalId);
      this.pollIntervals.delete(jobId);
    }
  }

  async openJob(job) {
    if (!this.modal) return;

    if (!TERMINAL.has(job.status)) {
      showToast("Hasil masih diproses.", "info");
      this.startPolling(job.id);
    }

    let current = job;
    if (job.status === "success" || job.status === "failed") {
      try {
        current = await fetchGenerateJob(job.id);
        this.upsertJob(current);
      } catch {
        /* pakai data cache */
      }
    }

    this.activeJobId = current.id;
    const action = ACTION_META[current.action] || { label: current.action };
    if (this.modalTitle) {
      this.modalTitle.textContent = current.title || action.label;
    }
    if (this.modalSubtitle) {
      this.modalSubtitle.textContent = action.label;
    }

    await renderResultBody(this.modalBody, current);

    if (this.btnCopy) {
      const canCopy = current.status === "success" && current.result && (current.action === "summary" || current.action === "table");
      if (canCopy) {
        this.btnCopy.classList.remove("hidden");
      } else {
        this.btnCopy.classList.add("hidden");
      }
    }

    this.modal.classList.remove("hidden");
    this.modal.classList.add("flex");
    document.body.classList.add("overflow-hidden");
  }

  closeModal() {
    if (!this.modal) return;
    this.modal.classList.add("hidden");
    this.modal.classList.remove("flex");
    document.body.classList.remove("overflow-hidden");
    if (this.btnCopy) {
      this.btnCopy.classList.add("hidden");
    }
    this.activeJobId = null;
  }

  async deleteActiveJob() {
    if (!this.activeJobId) return;
    const jobId = this.activeJobId;
    try {
      await deleteGenerateJob(jobId);
      this.stopPolling(jobId);
      this.jobsById.delete(jobId);
      this.listEl.querySelector(`[data-generate-job-id="${jobId}"]`)?.remove();
      if (this.listEl.querySelectorAll("[data-generate-job-id]").length === 0 && this.emptyEl) {
        this.emptyEl.classList.remove("hidden");
      }
      this.closeModal();
      showToast("Hasil generate dihapus.", "success");
    } catch (err) {
      showToast(err.message || "Gagal menghapus hasil.", "error");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const wsData = document.getElementById("workspace-data");
  if (!wsData?.dataset.workspaceId) return;
  if (!document.querySelector("[data-generate-shell]")) return;

  window.workspaceGenerate = new WorkspaceGenerate(wsData.dataset.workspaceId);
  window.workspaceGenerate.init();
});
