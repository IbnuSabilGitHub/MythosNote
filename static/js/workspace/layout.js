(function () {
  const isDesktop = () => window.matchMedia("(min-width: 1024px)").matches;

  const setHeaderAlignment = (header, collapsed) => {
    if (!header) return;
    header.classList.toggle("justify-between", !collapsed);
    header.classList.toggle("justify-center", collapsed);
  };

  const createLayoutController = () => {
    const sourcesShell = document.querySelector("[data-sources-shell]");
    const sourcesHeader = document.querySelector("[data-sources-header]");
    const sourcesToggles = Array.from(
      document.querySelectorAll("[data-sources-toggle]")
    );
    const sourcesPanels = Array.from(
      document.querySelectorAll("[data-sources-panel]")
    );
    const sourcesRail = document.querySelector("[data-sources-rail]");
    const sourcesChevrons = Array.from(
      document.querySelectorAll("[data-sources-chevron]")
    );
    const sourcesLabels = Array.from(
      document.querySelectorAll("[data-sources-label]")
    );

    const generateShell = document.querySelector("[data-generate-shell]");
    const generateHeader = document.querySelector("[data-generate-header]");
    const generateToggles = Array.from(
      document.querySelectorAll("[data-generate-toggle]")
    );
    const generatePanels = Array.from(
      document.querySelectorAll("[data-generate-panel]")
    );
    const generateRail = document.querySelector("[data-generate-rail]");
    const generateChevrons = Array.from(
      document.querySelectorAll("[data-generate-chevron]")
    );
    const generateLabels = Array.from(
      document.querySelectorAll("[data-generate-label]")
    );

    const mobileTabButtons = Array.from(
      document.querySelectorAll("[data-mobile-tab]")
    );
    const mobilePanels = Array.from(
      document.querySelectorAll("[data-mobile-panel]")
    );

    const defaultMobileTab =
      mobileTabButtons.find((button) =>
        button.hasAttribute("data-mobile-default")
      )?.dataset.mobileTab || mobileTabButtons[0]?.dataset.mobileTab;
    let activeMobileTab = defaultMobileTab;

    const setActiveMobileTab = (tabName) => {
      if (!tabName) return;
      activeMobileTab = tabName;
      mobilePanels.forEach((panel) => {
        const isHidden = panel.dataset.mobilePanel !== tabName;
        panel.classList.toggle("hidden", isHidden);
        if (isHidden) {
          panel.classList.remove("flex");
        } else {
          panel.classList.add("flex");
        }
      });
      mobileTabButtons.forEach((button) => {
        const isActive = button.dataset.mobileTab === tabName;
        button.setAttribute("aria-selected", String(isActive));
        button.classList.toggle("text-[#FFC880]", isActive);
        button.classList.toggle("text-stone-400", !isActive);
        button.classList.toggle("border-[#FFC880]", isActive);
        button.classList.toggle("border-transparent", !isActive);
      });
    };

    const setDesktopCollapsed = (collapsed) => {
      if (!sourcesShell) return;
      sourcesShell.dataset.collapsed = collapsed ? "true" : "false";
      sourcesShell.style.width = collapsed ? "3.5rem" : "";
      if (sourcesRail) {
        sourcesRail.classList.toggle("hidden", !collapsed);
      }

      sourcesPanels.forEach((panel) => {
        panel.classList.toggle("lg:flex", !collapsed);
        panel.classList.toggle("lg:hidden", collapsed);
      });

      sourcesToggles.forEach((button) => {
        button.setAttribute("aria-expanded", String(!collapsed));
        button.setAttribute("title", collapsed ? "Buka Panel" : "Tutup Panel");
      });
      sourcesChevrons.forEach((icon) => {
        icon.classList.toggle("rotate-180", !collapsed);
      });
      sourcesLabels.forEach((label) => {
        label.classList.toggle("hidden", collapsed);
      });
      setHeaderAlignment(sourcesHeader, collapsed);
    };

    const setGenerateCollapsed = (collapsed) => {
      if (!generateShell) return;
      generateShell.dataset.collapsed = collapsed ? "true" : "false";
      generateShell.style.width = collapsed ? "3.5rem" : "";
      if (generateRail) {
        generateRail.classList.toggle("hidden", !collapsed);
      }

      generatePanels.forEach((panel) => {
        panel.classList.toggle("lg:flex", !collapsed);
        panel.classList.toggle("lg:hidden", collapsed);
      });

      generateToggles.forEach((button) => {
        button.setAttribute("aria-expanded", String(!collapsed));
        button.setAttribute("title", collapsed ? "Buka Panel" : "Tutup Panel");
      });
      generateChevrons.forEach((icon) => {
        icon.classList.toggle("rotate-180", !collapsed);
      });
      generateLabels.forEach((label) => {
        label.classList.toggle("hidden", collapsed);
      });
      setHeaderAlignment(generateHeader, collapsed);
    };

    const toggleMobilePanels = () => {
      if (sourcesPanels.length === 0) return;
      const isHidden = sourcesPanels[0].classList.contains("hidden");
      sourcesPanels.forEach((panel) => {
        panel.classList.toggle("hidden", !isHidden);
        panel.classList.toggle("flex", isHidden);
      });
      sourcesToggles.forEach((button) => {
        button.setAttribute("aria-expanded", String(isHidden));
      });
      sourcesChevrons.forEach((icon) => {
        icon.classList.toggle("rotate-180", isHidden);
      });
    };

    sourcesToggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        if (isDesktop()) {
          const collapsed = sourcesShell?.dataset.collapsed === "true";
          setDesktopCollapsed(!collapsed);
        } else {
          toggleMobilePanels();
        }
      });
    });

    generateToggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        if (!isDesktop()) return;
        const collapsed = generateShell?.dataset.collapsed === "true";
        setGenerateCollapsed(!collapsed);
      });
    });

    window.addEventListener("resize", () => {
      if (isDesktop()) {
        mobilePanels.forEach((panel) => {
          panel.classList.remove("hidden");
          if (panel.dataset.mobilePanel === 'generate') {
            panel.classList.remove("flex");
          } else {
            panel.classList.add("flex");
          }
        });
      } else {
        if (sourcesShell) {
          sourcesShell.style.width = "";
          sourcesShell.dataset.collapsed = "false";
        }
        if (sourcesRail) {
          sourcesRail.classList.add("hidden");
        }
        sourcesPanels.forEach((panel) => {
          panel.classList.remove("lg:hidden");
          panel.classList.add("lg:flex");
        });
        sourcesLabels.forEach((label) => {
          label.classList.remove("hidden");
        });
        setHeaderAlignment(sourcesHeader, false);

        if (generateShell) {
          generateShell.style.width = "";
          generateShell.dataset.collapsed = "false";
        }
        if (generateRail) {
          generateRail.classList.add("hidden");
        }
        generatePanels.forEach((panel) => {
          panel.classList.remove("lg:hidden");
          panel.classList.add("lg:flex");
        });
        generateLabels.forEach((label) => {
          label.classList.remove("hidden");
        });
        setHeaderAlignment(generateHeader, false);

        setActiveMobileTab(activeMobileTab || defaultMobileTab);
      }
    });

    if (mobileTabButtons.length > 0 && !isDesktop()) {
      setActiveMobileTab(activeMobileTab || defaultMobileTab);
    }

    if (sourcesRail) {
      sourcesRail.classList.add("hidden");
    }
    if (generateRail) {
      generateRail.classList.add("hidden");
    }

    mobileTabButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (isDesktop()) return;
        setActiveMobileTab(button.dataset.mobileTab);
      });
    });
  };

  window.WorkspaceLayout = {
    init() {
      createLayoutController();
    }
  };
})();
