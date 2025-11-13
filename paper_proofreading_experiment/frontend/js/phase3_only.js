const state = {
    paperId: '',
    maxIterations: 0,
    nextIteration: 1,
};

const elements = {};

function cacheElements() {
    elements.sessionForm = document.getElementById('session-form');
    elements.paperInput = document.getElementById('paper-id-input');
    elements.maxIterationsInput = document.getElementById('max-iterations-input');
    elements.sessionHint = document.getElementById('session-hint');
    elements.statusCard = document.getElementById('status-card');
    elements.nextIterationLabel = document.getElementById('next-iteration-label');
    elements.progressBar = document.getElementById('iteration-progress');
    elements.progressHint = document.getElementById('progress-hint');
    elements.sessionBadge = document.getElementById('session-badge');
    elements.iterationForm = document.getElementById('iteration-form');
    elements.iterationInput = document.getElementById('iteration-input');
    elements.texInput = document.getElementById('tex-file-input');
    elements.pdfInput = document.getElementById('pdf-file-input');
    elements.uploadBtn = document.getElementById('upload-btn');
    elements.uploadHint = document.getElementById('upload-hint');
    elements.iterationHelper = document.getElementById('iteration-helper');
    elements.historyBody = document.getElementById('history-body');
    elements.historyCounter = document.getElementById('history-counter');
    elements.logFeed = document.getElementById('log-feed');
    elements.resetButton = document.getElementById('reset-session-btn');
}

function addLog(message, variant = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry border-start border-4 border-${variant}`;
    entry.innerHTML = `
        <div>${message}</div>
        <small>${new Date().toLocaleString()}</small>
    `;
    if (elements.logFeed.firstElementChild && elements.logFeed.firstElementChild.classList.contains('text-muted')) {
        elements.logFeed.innerHTML = '';
    }
    elements.logFeed.prepend(entry);
}

function updateProgress() {
    if (!state.paperId) {
        elements.statusCard.style.display = 'none';
        return;
    }

    elements.statusCard.style.display = 'block';
    elements.nextIterationLabel.textContent = state.nextIteration;

    const progress = Math.min(((state.nextIteration - 1) / state.maxIterations) * 100, 100);
    elements.progressBar.style.width = `${progress}%`;
    elements.progressHint.textContent = `${state.nextIteration - 1} / ${state.maxIterations} 回アップロード済み`;

    if (state.nextIteration > state.maxIterations) {
        elements.sessionBadge.textContent = '上限に達しました';
        elements.sessionBadge.className = 'badge rounded-pill text-bg-secondary';
        elements.iterationHelper.textContent = '最大イテレーションに到達しました';
        toggleUploadForm(false);
    } else {
        elements.sessionBadge.textContent = '受付中';
        elements.sessionBadge.className = 'badge rounded-pill text-bg-success';
        elements.iterationHelper.textContent = '次のイテレーションを登録してください';
        toggleUploadForm(true);
    }
}

function toggleUploadForm(enabled) {
    elements.texInput.disabled = !enabled;
    elements.pdfInput.disabled = !enabled;
    elements.uploadBtn.disabled = !enabled;
}

async function handleSessionSubmit(event) {
    event.preventDefault();
    const paperId = elements.paperInput.value.trim();
    const maxIterations = parseInt(elements.maxIterationsInput.value, 10);

    if (!paperId || Number.isNaN(maxIterations) || maxIterations < 1) {
        addLog('論文IDと最大イテレーションを確認してください', 'danger');
        return;
    }

    state.paperId = paperId;
    state.maxIterations = maxIterations;
    elements.sessionHint.textContent = `論文ID: ${paperId}`;
    elements.resetButton.disabled = false;
    addLog(`セッションを開始しました (最大 ${maxIterations} 回)`, 'success');

    await loadIterations();
}

async function loadIterations() {
    if (!state.paperId) return;

    try {
        const response = await axios.get(`/api/phase3-only/iterations/${encodeURIComponent(state.paperId)}`);
        const { iterations = [], next_iteration: nextIteration = 1 } = response.data;

        state.nextIteration = nextIteration;
        elements.historyCounter.textContent = `${iterations.length}件`;
        elements.iterationInput.value = nextIteration;

        if (iterations.length === 0) {
            elements.historyBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">アップロードはまだありません</td></tr>';
        } else {
            elements.historyBody.innerHTML = iterations
                .sort((a, b) => a.iteration - b.iteration)
                .map((item) => `
                    <tr>
                        <td><span class="badge rounded-pill text-bg-primary">${item.iteration}</span></td>
                        <td><a href="${item.tex_url}" class="link-primary" target="_blank">${item.tex_filename}</a></td>
                        <td><a href="${item.pdf_url}" class="link-primary" target="_blank">${item.pdf_filename}</a></td>
                        <td><small class="text-muted">${new Date(item.uploaded_at).toLocaleString()}</small></td>
                    </tr>
                `).join('');
        }

        updateProgress();
    } catch (error) {
        console.error(error);
        addLog('履歴の取得に失敗しました', 'danger');
    }
}

async function handleIterationSubmit(event) {
    event.preventDefault();
    if (!state.paperId) {
        addLog('先にセッションを開始してください', 'warning');
        return;
    }

    if (state.nextIteration > state.maxIterations) {
        addLog('指定した最大イテレーション数に達しました', 'warning');
        return;
    }

    if (!elements.texInput.files.length || !elements.pdfInput.files.length) {
        addLog('TeXとPDFの両方を選択してください', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('paper_id', state.paperId);
    formData.append('iteration', state.nextIteration);
    formData.append('tex_file', elements.texInput.files[0]);
    formData.append('pdf_file', elements.pdfInput.files[0]);

    toggleUploadForm(false);
    elements.iterationHelper.textContent = 'アップロード中...';

    try {
        await axios.post('/api/phase3-only/iterations', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        addLog(`イテレーション${state.nextIteration}を登録しました`, 'success');
        elements.iterationForm.reset();
    } catch (error) {
        const message = error.response?.data?.detail || 'アップロードに失敗しました';
        addLog(message, 'danger');
    } finally {
        await loadIterations();
        toggleUploadForm(true);
    }
}

async function handleReset() {
    if (!state.paperId) return;
    if (!confirm('アップロード済みのファイルをすべて削除します。続行しますか？')) {
        return;
    }

    try {
        await axios.delete(`/api/phase3-only/iterations/${encodeURIComponent(state.paperId)}`);
        addLog('アップロードをリセットしました', 'warning');
        state.nextIteration = 1;
        await loadIterations();
    } catch (error) {
        addLog('リセットに失敗しました', 'danger');
    }
}

function init() {
    cacheElements();
    elements.sessionForm.addEventListener('submit', handleSessionSubmit);
    elements.iterationForm.addEventListener('submit', handleIterationSubmit);
    elements.resetButton.addEventListener('click', handleReset);
    toggleUploadForm(false);
}

document.addEventListener('DOMContentLoaded', init);
