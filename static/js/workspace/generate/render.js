import { marked } from "marked";
import { ACTION_META, STATUS_META } from "./constants.js";

marked.setOptions({ breaks: true });

function escapeHtml(text) {
  return window.MythosDom?.escapeHtml?.(text) ?? String(text ?? "");
}

function formatJobTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  const sameDay =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear();
  const time = date.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
  if (sameDay) return `Hari ini, ${time}`;
  return date.toLocaleString("id-ID", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sourceCountLabel(count) {
  const n = Number(count) || 0;
  return `${n} ${n === 1 ? "Source" : "Sources"}`;
}

function statusBadgeHtml(status) {
  const meta = STATUS_META[status] || { label: status, tone: "pending" };
  if (meta.tone === "success") {
    return `<div class="px-2 py-0.5 bg-green-500/10 rounded-xs outline -outline-offset-1 outline-green-500/25 inline-flex flex-col justify-start items-start">
      <div class="h-4 justify-center text-teal-400 text-[10px] font-normal font-['Manrope'] leading-4">${escapeHtml(meta.label)}</div>
    </div>`;
  }
  if (meta.tone === "failed") {
    return `<div class="px-2 py-0.5 bg-red-500/10 rounded-xs outline -outline-offset-1 outline-red-500/25 inline-flex flex-col justify-start items-start">
      <div class="h-4 justify-center text-red-400 text-[10px] font-normal font-['Manrope'] leading-4">${escapeHtml(meta.label)}</div>
    </div>`;
  }
  return `<div class="px-2 py-0.5 bg-primary/10 rounded-xs outline-1 -outline-offset-1 outline-primary/50 flex justify-start items-center gap-1">
    <div class="w-1.5 h-1.5 bg-yellow-400 rounded-xl animate-pulse"></div>
    <div class="h-4 justify-center text-primary text-[10px] font-normal font-['Manrope'] leading-4">${escapeHtml(meta.label)}</div>
  </div>`;
}

export function renderJobCard(job) {
  const action = ACTION_META[job.action] || { label: job.action, icon: "tabler:sparkles" };
  const title = job.title || action.label;
  const count = Array.isArray(job.source_ids) ? job.source_ids.length : 0;
  const timeLabel = formatJobTime(job.created_at);

  const card = document.createElement("button");
  card.type = "button";
  card.dataset.generateJobId = job.id;
  card.className =
    "self-stretch p-2 bg-neutral-900/70 rounded-lg border border-neutral-800 flex flex-col justify-start items-start gap-2 cursor-pointer hover:bg-neutral-800/50 transition text-left";
// eslint-disable-next-line no-unsanitized/property
  card.innerHTML = `
    <div class="self-stretch inline-flex justify-between items-start">
      <div class="flex justify-start items-center gap-2 min-w-0">
        <iconify-icon icon="${escapeHtml(action.icon)}" class="text-primary text-sm shrink-0"></iconify-icon>
        <div class="inline-flex flex-col justify-start items-start min-w-0">
          <div class="h-5 justify-center text-zinc-200 text-xs font-medium font-['Manrope'] leading-5 truncate max-w-[11rem]">${escapeHtml(title)}</div>
        </div>
      </div>
      ${statusBadgeHtml(job.status)}
    </div>
    <div class="self-stretch flex flex-col justify-start items-start">
      <div class="self-stretch justify-center text-stone-300 text-xs font-normal font-['Manrope'] leading-4">${escapeHtml(timeLabel)} • ${escapeHtml(sourceCountLabel(count))}</div>
    </div>
  `;
  return card;
}

function renderQuizHtml(resultText) {
  let data;
  try {
    data = JSON.parse(resultText);
  } catch {
    return `<p class="text-red-400 text-sm">Format kuis tidak valid.</p>`;
  }

  const questions = data?.questions;
  if (!Array.isArray(questions) || questions.length === 0) {
    return `<p class="text-stone-400 text-sm">Tidak ada pertanyaan.</p>`;
  }

  return questions
    .map((item, index) => {
      const options = (item.options || [])
        .map(
          (opt) =>
            `<li class="text-stone-300 text-sm font-['Manrope'] leading-5">${escapeHtml(opt)}</li>`
        )
        .join("");
      const explanation = item.explanation
        ? `<p class="mt-2 text-xs text-stone-500 font-['Manrope']">${escapeHtml(item.explanation)}</p>`
        : "";
      return `<article class="rounded-lg border border-neutral-800 bg-neutral-950/50 p-4">
        <p class="text-zinc-100 text-sm font-semibold font-['Manrope'] mb-2">${index + 1}. ${escapeHtml(item.question || "")}</p>
        <ul class="list-disc pl-5 space-y-1">${options}</ul>
        <p class="mt-3 text-xs text-primary font-['Manrope']">Jawaban: ${escapeHtml(item.answer || "")}</p>
        ${explanation}
      </article>`;
    })
    .join("");
}

async function renderMindmapHtml(container, code) {
  if (!window.mermaid?.render) {
// eslint-disable-next-line no-unsanitized/property
    container.innerHTML = `<pre class="text-xs text-stone-400 whitespace-pre-wrap font-mono">${escapeHtml(code)}</pre>`;
    return;
  }
  const renderId = `generate-mmd-${Date.now()}`;
  try {
    const { svg } = await window.mermaid.render(renderId, code);
// eslint-disable-next-line no-unsanitized/property
    container.innerHTML = `<div class="generate-mermaid overflow-x-auto">${svg}</div>`;
  } catch (err) {
// eslint-disable-next-line no-unsanitized/property
    container.innerHTML = `<pre class="text-xs text-red-400 whitespace-pre-wrap">${escapeHtml(err.message || "Gagal render mindmap.")}</pre>`;
  }
}

export async function renderResultBody(container, job) {
  if (!container) return;
 
  container.innerHTML = "";

  if (job.status === "failed") {
// eslint-disable-next-line no-unsanitized/property
    container.innerHTML = `<p class="text-red-400 text-sm font-['Manrope']">${escapeHtml(job.error_message || "Generate gagal.")}</p>`;
    return;
  }

  if (job.status !== "success" || !job.result) {
 
    container.innerHTML = `<p class="text-stone-400 text-sm font-['Manrope'] animate-pulse">Menunggu hasil...</p>`;
    return;
  }

  const result = job.result;

  if (job.action === "quiz") {
// eslint-disable-next-line no-unsanitized/property
    container.innerHTML = `<div class="flex flex-col gap-3">${renderQuizHtml(result)}</div>`;
    return;
  }

  if (job.action === "mindmap") {
    const wrap = document.createElement("div");
    container.appendChild(wrap);
    await renderMindmapHtml(wrap, result);
    return;
  }

  const markdownWrap = document.createElement("div");
  markdownWrap.className = "chat-markdown";
// eslint-disable-next-line no-unsanitized/property
  markdownWrap.innerHTML = marked.parse(result);
  container.appendChild(markdownWrap);
}

export function setGenerateButtonsLoading(buttons, action, loading) {
  buttons.forEach((btn) => {
    if (btn.dataset.generateAction !== action) return;
    btn.disabled = loading;
    const hint = btn.querySelector("[data-generate-hint]");
    if (hint) {
      hint.textContent = loading ? "Memproses..." : "";
      hint.classList.toggle("hidden", !loading);
    }
  });
}
