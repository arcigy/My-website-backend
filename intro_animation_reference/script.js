// JavaScript to control the timing of the Intro Animation

function initIntroOverlay() {
    const overlay = document.getElementById('Intro_Overlay');
    if (!overlay) return;

    // Lock scroll (optional for standalone)
    document.body.style.overflow = 'hidden';

    // Animation Sequence timed in "beats"

    // Beat 1: Text Fade In (at 0.2s)
    setTimeout(() => {
        const textPaths = overlay.querySelectorAll('.path-text');
        textPaths.forEach((path) => {
            path.classList.add('anim-text');
        });
    }, 200);

    // Beat 2: Left Bracket (at 0.6s)
    setTimeout(() => {
        const leftBracket = overlay.querySelector('.path-symbol-left');
        if (leftBracket) leftBracket.classList.add('anim-symbol');
    }, 600);

    // Beat 3: Slash (at 0.8s)
    setTimeout(() => {
        const slash = overlay.querySelector('.path-symbol-slash');
        if (slash) slash.classList.add('anim-symbol');
    }, 800);

    // Beat 4: Right Bracket (at 1.0s)
    setTimeout(() => {
        const rightBracket = overlay.querySelector('.path-symbol-right');
        if (rightBracket) rightBracket.classList.add('anim-symbol');
    }, 1000);

    // End: Fade Out the entire overlay (at 1.5s)
    setTimeout(() => {
        overlay.classList.add('fade-out');
        document.body.style.overflow = ''; // Unlock scroll

        // In the real app, we mark session as shown here
        // sessionStorage.setItem('introShown', 'true');
    }, 1500);
}
