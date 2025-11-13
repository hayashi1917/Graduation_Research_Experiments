const form = document.getElementById('phase3-form');
const statusArea = document.getElementById('status-area');

function showStatus(message, variant = 'info') {
    statusArea.classList.remove('d-none', 'alert-info', 'alert-success', 'alert-danger');
    statusArea.classList.add(`alert-${variant}`);
    statusArea.textContent = message;
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const paperId = document.getElementById('paper-id').value.trim();
    const iteration = parseInt(document.getElementById('iteration').value, 10);
    const texFile = document.getElementById('tex-file').files[0];
    const pdfFile = document.getElementById('pdf-file').files[0];

    if (!paperId || Number.isNaN(iteration) || iteration < 1 || !texFile || !pdfFile) {
        showStatus('すべての項目を入力してください。', 'danger');
        return;
    }

    const formData = new FormData();
    formData.append('paper_id', paperId);
    formData.append('iteration', iteration);
    formData.append('tex_file', texFile);
    formData.append('pdf_file', pdfFile);

    form.querySelector('button[type="submit"]').disabled = true;
    showStatus('アップロード中です...', 'info');

    try {
        const response = await axios.post('/api/phase3-only/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        showStatus(response.data?.message ?? 'アップロードが完了しました。', 'success');
        document.getElementById('tex-file').value = '';
        document.getElementById('pdf-file').value = '';
    } catch (error) {
        const detail = error.response?.data?.detail || 'アップロードに失敗しました。';
        showStatus(detail, 'danger');
    } finally {
        form.querySelector('button[type="submit"]').disabled = false;
    }
});
