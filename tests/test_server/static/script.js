// VRCPost テストサーバー用スクリプト

/**
 * 投稿フォームの画像プレビュー
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
 * 予約投稿の日時入力を表示/非表示
 */
function toggleSchedule() {
    const input = document.getElementById('schedule-input');
    if (input.style.display === 'none') {
        input.style.display = 'block';
        // 現在時刻 + 1時間をデフォルトに
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
 * Ctrl+Enter で投稿
 */
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        const form = document.getElementById('post-form');
        if (form) {
            form.submit();
        }
    }
});
