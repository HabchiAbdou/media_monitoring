document.addEventListener("DOMContentLoaded", () => {
    // Highlight urgent mentions
    document.querySelectorAll(".mention[data-urgent='true']").forEach((el) => {
        el.classList.add("is-urgent");
    });

    // Mobile nav toggle
    const menuToggle = document.querySelector(".menu-toggle");
    const nav = document.getElementById("primary-nav");
    if (menuToggle && nav) {
        menuToggle.addEventListener("click", () => {
            const isOpen = nav.classList.toggle("nav-open");
            menuToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
    }

    // Theme handling
    const body = document.body;
    const root = document.documentElement;
    const themeToggle = document.querySelector(".theme-toggle");
    const themeStorageKey = "media-monitoring-theme";
    const getStoredTheme = () => {
        try {
            return localStorage.getItem(themeStorageKey);
        } catch (error) {
            return null;
        }
    };
    const setStoredTheme = (mode) => {
        try {
            localStorage.setItem(themeStorageKey, mode);
        } catch (error) {
            // Ignore storage errors to keep the UI responsive
        }
    };
    const applyTheme = (mode) => {
        const useDark = mode === "dark";
        body.classList.toggle("dark-mode", useDark);
        root.classList.toggle("dark-mode", useDark);
        root.setAttribute("data-theme", useDark ? "dark" : "light");
        if (themeToggle) {
            themeToggle.setAttribute("aria-checked", useDark ? "true" : "false");
        }
    };
    const storedPreference = getStoredTheme();
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initialMode = storedPreference || (prefersDark ? "dark" : "light");
    applyTheme(initialMode);
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const nextMode = body.classList.contains("dark-mode") ? "light" : "dark";
            applyTheme(nextMode);
            setStoredTheme(nextMode);
        });
        themeToggle.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                themeToggle.click();
            }
        });
    }

    // Smooth scroll for internal links
    document.querySelectorAll("a[href^='#']").forEach((anchor) => {
        anchor.addEventListener("click", (e) => {
            const targetId = anchor.getAttribute("href").slice(1);
            const target = document.getElementById(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

    // Monitor button: trigger scraping/LLM pipeline on demand
    const monitorButton = document.getElementById("monitor-button");
    const statusText = document.getElementById("monitor-status");

    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return "";
    };

    if (monitorButton) {
        monitorButton.addEventListener("click", () => {
            monitorButton.disabled = true;
            monitorButton.textContent = "Veille en cours...";
            if (statusText) statusText.textContent = "Le site collecte les donnees sur vos sources, veuillez patienter...";

            fetch("/run-monitor/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({}),
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error("Server error");
                    }
                    return response.json().catch(() => ({}));
                })
                .then((data) => {
                    const processed = (data && data.processed) || 0;
                    if (statusText) statusText.textContent = `Veille terminee (${processed} URL traitees). Actualisation du tableau de bord...`;
                    setTimeout(() => {
                        window.location.reload();
                    }, 800);
                })
                .catch((error) => {
                    if (statusText) statusText.textContent = "Une erreur s'est produite. Veuillez reessayer.";
                    monitorButton.disabled = false;
                    monitorButton.textContent = "Lancer la veille";
                    console.error(error);
                });
        });
    }
});
