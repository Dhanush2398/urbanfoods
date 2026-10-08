document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    // Navbar scroll effect - Shrink and Glassmorphism
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        // Remove bg-transparent if it exists initially on load if scrolled
        if (window.scrollY > 20) {
            navbar.classList.add('glass-panel', 'py-2');
            navbar.classList.remove('py-3', 'bg-white', 'bg-transparent');
        }

        window.addEventListener('scroll', () => {
            if (window.scrollY > 20) {
                // Scrolled state
                navbar.classList.add('glass-panel', 'py-2', 'shadow-sm');
                navbar.classList.remove('py-3', 'bg-white', 'bg-transparent');
            } else {
                // Top state
                navbar.classList.remove('glass-panel', 'py-2', 'shadow-sm');
                // We add bg-white back if it was originally there, assuming most pages use bg-white at the top
                // For pages with hero images (like index.html), we might need specific classes.
                // By default, we keep it py-3.
                navbar.classList.add('py-3', 'bg-white');
            }
        });
    }

    // Scroll reveal animation
    const revealElements = document.querySelectorAll('.animate-fade-up');
    const revealOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const revealOnScroll = new IntersectionObserver(function(entries, observer) {
        entries.forEach(entry => {
            if (!entry.isIntersecting) {
                return;
            } else {
                entry.target.style.animationPlayState = 'running';
                observer.unobserve(entry.target);
            }
        });
    }, revealOptions);

    revealElements.forEach(el => {
        el.style.animationPlayState = 'paused';
        revealOnScroll.observe(el);
    });
});
