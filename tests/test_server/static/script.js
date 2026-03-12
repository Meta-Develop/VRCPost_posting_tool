// VRCPost test server script

/**
 * Preview images in the post form
 */
function previewImages(input) {
    const container = document.getElementById('image-preview-container');
    container.innerHTML = '';

    if (!input.files) return;

    for (const file of input.files) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.createElement('img');
            img.src = e.target.result;
            container.appendChild(img);
        };
        reader.readAsDataURL(file);
    }
}

/**
 * Toggle scheduled post datetime input
 */
function toggleSchedule() {
    const input = document.getElementById('schedule-input');
    if (input.style.display === 'none') {
        input.style.display = 'block';
        // Default to current time + 1 hour
        const now = new Date();
        now.setHours(now.getHours() + 1);
        now.setMinutes(0);
        input.value = now.toISOString().slice(0, 16);
    } else {
        input.style.display = 'none';
        input.value = '';
    }
}

/**
 * Submit post with Ctrl+Enter
 */
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        const form = document.getElementById('post-form');
        if (form) {
            form.submit();
        }
    }
});
