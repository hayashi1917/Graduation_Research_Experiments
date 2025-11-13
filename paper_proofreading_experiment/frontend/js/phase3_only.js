const form = document.getElementById('phase3-form');
const statusArea = document.getElementById('status-area');
const resultCard = document.getElementById('result-card');
const resultSummary = document.getElementById('result-summary');
const excludedWrapper = document.getElementById('excluded-wrapper');
const excludedList = document.getElementById('excluded-list');
const issuesWrapper = document.getElementById('issues-wrapper');
const issuesList = document.getElementById('issues-list');
const submitButton = form.querySelector('button[type="submit"]');

function showStatus(message, variant = 'info') {
    statusArea.classList.remove('d-none', 'alert-info', 'alert-success', 'alert-danger');
    statusArea.classList.add(`alert-${variant}`);
    statusArea.textContent = message;
}

function resetResults() {
    resultCard.classList.add('d-none');
    resultSummary.textContent = '';
    excludedWrapper.classList.add('d-none');
    excludedList.innerHTML = '';
    issuesWrapper.classList.add('d-none');
    issuesList.innerHTML = '';
}

function createTextBlock(label, text) {
    const wrapper = document.createElement('div');
    wrapper.className = 'mb-2';

    const labelEl = document.createElement('div');
    labelEl.className = 'text-muted small';
    labelEl.textContent = label;

    const contentEl = document.createElement('p');
    contentEl.className = 'mb-0';
    contentEl.textContent = text;

    wrapper.append(labelEl, contentEl);
    return wrapper;
}

function createIssueElement(issue, index) {
    const container = document.createElement('div');
    container.className = 'list-group-item px-0';

    const header = document.createElement('div');
    header.className = 'fw-semibold mb-2';
    header.textContent = `指摘 ${issue.issue_number ?? index}`;
    container.appendChild(header);

    container.appendChild(createTextBlock('修正前', issue.before ?? ''));
    container.appendChild(createTextBlock('根拠', issue.reasoning ?? ''));
    container.appendChild(createTextBlock('修正後', issue.after ?? ''));

    return container;
}

function renderResults(payload) {
    if (!payload) {
        resetResults();
        return;
    }

    resultSummary.textContent = payload.message ?? '';

    if (payload.excluded_items && payload.excluded_items.length) {
        excludedWrapper.classList.remove('d-none');
        excludedList.innerHTML = '';
        payload.excluded_items.forEach((item) => {
            const li = document.createElement('li');
            li.className = 'list-group-item px-0';
            li.textContent = item;
            excludedList.appendChild(li);
        });
    } else {
        excludedWrapper.classList.add('d-none');
        excludedList.innerHTML = '';
    }

    issuesList.innerHTML = '';
    if (!payload.no_issues && payload.issues && payload.issues.length) {
        issuesWrapper.classList.remove('d-none');
        payload.issues.forEach((issue, index) => {
            issuesList.appendChild(createIssueElement(issue, index + 1));
        });
    } else {
        issuesWrapper.classList.add('d-none');
    }

    resultCard.classList.remove('d-none');
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const paperId = document.getElementById('paper-id').value.trim();
    const texFile = document.getElementById('tex-file').files[0];
    const pdfFile = document.getElementById('pdf-file').files[0];
    const excludedItems = document.getElementById('excluded-items').value.trim();

    if (!paperId || !texFile || !pdfFile) {

        showStatus('すべての項目を入力してください。', 'danger');
        return;
    }

    const formData = new FormData();
    formData.append('paper_id', paperId);
    formData.append('tex_file', texFile);
    formData.append('pdf_file', pdfFile);
    formData.append('excluded_items', excludedItems);

    submitButton.disabled = true;
    resetResults();
    showStatus('校正中です...', 'info');

    try {
        const response = await axios.post('/api/phase3-only/proofread', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        showStatus(response.data?.message ?? '校正が完了しました。', 'success');
        renderResults(response.data);
        document.getElementById('tex-file').value = '';
        document.getElementById('pdf-file').value = '';
    } catch (error) {
        const detail = error.response?.data?.detail || '校正に失敗しました。';
        showStatus(detail, 'danger');
    } finally {
        submitButton.disabled = false;
    }
});
