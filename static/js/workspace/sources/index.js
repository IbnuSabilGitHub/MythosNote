import {
  fetchSources,
  renderSourceList,
  updatePanelSummary,
  showLoadingState,
  showErrorState,
  showErrorToast,
} from "./list.js";

import {
  createSourceItemHTML,
  getStatusClass,
  getStatusLabel,
  escapeHTML,
} from "./item.js";

import { uploadSource, pollSourceStatus, updateSourceItemStatus } from "./poll.js";
import { deleteSource } from "./delete.js";

(function attachToWindow() {
  class WorkspaceSources {
    constructor(workspaceId) {
      this.workspaceId = workspaceId;
      this.container = document.querySelector("#source-list-container");
      this.countEl = document.querySelector("[data-source-count]");
      this.statsEl = document.querySelector("[data-source-stats]");

      const maxAttr = document.querySelector("#workspace-data")?.dataset?.maxSources;
      const parsed = Number.parseInt(maxAttr, 10);
      this.maxSources = Number.isFinite(parsed) && parsed > 0 ? parsed : 5;

      this.pollIntervals = new Map();
    }

    getCSRFToken() {
      return (
        window.MythosCsrf?.getCsrfToken?.() ||
        document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
        ""
      );
    }

    async fetchSources(workspaceId = null) {
      return fetchSources.call(this, workspaceId);
    }

    renderSourceList(sources) {
      return renderSourceList.call(this, sources);
    }

    updatePanelSummary(sources) {
      return updatePanelSummary.call(this, sources);
    }

    createSourceItemHTML(source) {
      return createSourceItemHTML.call(this, source);
    }

    getStatusClass(status) {
      return getStatusClass(status);
    }

    getStatusLabel(status) {
      return getStatusLabel(status);
    }

    async uploadSource(formData) {
      return uploadSource.call(this, formData);
    }

    async pollSourceStatus(sourceId, interval = 2000) {
      return pollSourceStatus.call(this, sourceId, interval);
    }

    updateSourceItemStatus(sourceId, statusOrData) {
      return updateSourceItemStatus.call(this, sourceId, statusOrData);
    }

    async deleteSource(sourceId) {
      return deleteSource.call(this, sourceId);
    }

    showLoadingState() {
      return showLoadingState.call(this);
    }

    showErrorState(message) {
      return showErrorState.call(this, message);
    }

    showErrorToast(message) {
      return showErrorToast.call(this, message);
    }

    escapeHTML(text) {
      return escapeHTML.call(this, text);
    }
  }

  window.WorkspaceSources = WorkspaceSources;
})();

