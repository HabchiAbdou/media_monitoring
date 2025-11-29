document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".mention[data-urgent='true']").forEach((el) => {
        el.classList.add("is-urgent");
    });

    const menuToggle = document.querySelector(".menu-toggle");
    const nav = document.getElementById("primary-nav");

    if (menuToggle && nav) {
        menuToggle.addEventListener("click", () => {
            const isOpen = nav.classList.toggle("nav-open");
            menuToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
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
});
