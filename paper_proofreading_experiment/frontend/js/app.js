/**
 * メインアプリケーションロジック
 */

// アプリケーション状態
const AppState = {
    selectedPaperId: null,
    currentPhase: null,
    currentIssue: null,
    isRunning: false,
};

let skipModalInstance = null;

// ページロード時の初期化
document.addEventListener('DOMContentLoaded', () => {
    console.log('アプリケーション初期化');

    // WebSocket接続
    wsManager.connect();
    wsManager.addMessageHandler(handleWebSocketMessage);

    // イベントリスナーを設定
    setupEventListeners();

    // 初期データを読み込み
    loadPapers();
});

/**
 * イベントリスナーの設定
 */
function setupEventListeners() {
    // 設定ボタン
    document.getElementById('settings-btn').addEventListener('click', () => {
        const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
        loadSettings();
        modal.show();
    });

    // リセットボタン
    document.getElementById('reset-btn').addEventListener('click', () => {
        const modal = new bootstrap.Modal(document.getElementById('resetModal'));
        modal.show();
    });

    // リセット確認ボタン
    document.getElementById('reset-confirm-btn').addEventListener('click', handleReset);

    // 設定保存
    document.getElementById('settings-save-btn').addEventListener('click', saveSettings);

    // アップロードボタン
    document.getElementById('upload-submit-btn').addEventListener('click', handleUpload);

    // フェーズボタン
    document.getElementById('phase1-btn').addEventListener('click', () => startPhase('phase1'));
    document.getElementById('phase2-btn').addEventListener('click', () => startPhase('phase2'));
    document.getElementById('phase3-btn').addEventListener('click', () => startPhase('phase3'));

    // 指摘判断ボタン
    document.getElementById('action-accept').addEventListener('click', () => sendAction('A'));
    document.getElementById('action-skip').addEventListener('click', () => sendAction('S'));
    document.getElementById('action-quit').addEventListener('click', () => sendAction('Q'));

    // スキップモーダル
    document.getElementById('skip-submit-btn').addEventListener('click', handleSkipSubmit);
    const skipItemInput = document.getElementById('skip-item-input');
    skipItemInput.addEventListener('input', () => skipItemInput.classList.remove('is-invalid'));

    // コピーボタン
    document.getElementById('copy-before-btn').addEventListener('click', () => copyToClipboard('issue-before', 'copy-before-btn'));
    document.getElementById('copy-after-btn').addEventListener('click', () => copyToClipboard('issue-after', 'copy-after-btn'));

    // キーボードショートカット
    document.addEventListener('keydown', (e) => {
        if (document.getElementById('issue-card').style.display !== 'none') {
            switch (e.key.toLowerCase()) {
                case 'a':
                    sendAction('A');
                    break;
                case 'm':
                    sendAction('M');
                    break;
                case 's':
                    sendAction('S');
                    break;
                case 'd':
                    sendAction('D');
                    break;
                case 'q':
                    sendAction('Q');
                    break;
            }
        }
    });
}

/**
 * 論文リストを読み込み
 */
async function loadPapers() {
    try {
        const data = await API.getPapers();
        displayPapers(data.papers);
    } catch (error) {
        addLogMessage('論文リストの読み込みに失敗しました: ' + error.message, 'error');
    }
}

/**
 * 論文リストを表示
 */
function displayPapers(papers) {
    const papersList = document.getElementById('papers-list');

    if (papers.length === 0) {
        papersList.innerHTML = '<p class="text-muted">論文がありません</p>';
        return;
    }

    papersList.innerHTML = papers.map(paper => `
        <div class="paper-item" data-paper-id="${paper.id}">
            <div class="fw-bold">${paper.id}</div>
            <small>PDF: ${paper.pdf}</small>
        </div>
    `).join('');

    // 論文選択イベント
    papersList.querySelectorAll('.paper-item').forEach(item => {
        item.addEventListener('click', (e) => {
            selectPaper(e.currentTarget.dataset.paperId);
        });
    });
}

/**
 * 論文を選択
 */
async function selectPaper(paperId) {
    AppState.selectedPaperId = paperId;

    // UIを更新
    document.querySelectorAll('.paper-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-paper-id="${paperId}"]`)?.classList.add('active');

    // フェーズボタンを有効化
    document.getElementById('phase1-btn').disabled = false;
    document.getElementById('phase2-btn').disabled = false;
    document.getElementById('phase3-btn').disabled = false;

    addLogMessage(`論文を選択しました: ${paperId}`, 'info');

    // セッションを読み込み
    await loadSessions(paperId);

    // イテレーション履歴を読み込み
    loadIterations(paperId);
}

/**
 * 論文をアップロード
 */
async function handleUpload() {
    const paperId = document.getElementById('paper-id-input').value;
    const pdfFile = document.getElementById('pdf-file-input').files[0];

    if (!paperId || !pdfFile) {
        alert('すべての項目を入力してください');
        return;
    }

    try {
        addLogMessage(`論文をアップロード中: ${paperId}`, 'info');

        const result = await API.uploadPaper(paperId, pdfFile);

        addLogMessage(`アップロード成功: ${result.message}`, 'success');

        // モーダルを閉じる
        const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
        modal.hide();

        // フォームをリセット
        document.getElementById('upload-form').reset();

        // 論文リストを再読み込み
        loadPapers();
    } catch (error) {
        addLogMessage(`アップロードエラー: ${error.message}`, 'error');
    }
}

/**
 * フェーズを開始
 */
function startPhase(phase) {
    if (!AppState.selectedPaperId) {
        alert('論文を選択してください');
        return;
    }

    if (AppState.isRunning) {
        alert('既に実行中です');
        return;
    }

    AppState.currentPhase = phase;
    AppState.isRunning = true;

    // UIを更新
    showStatusCard(phase);
    disablePhaseButtons();

    // WebSocketでフェーズ開始を送信
    wsManager.send({
        type: 'start_phase',
        paper_id: AppState.selectedPaperId,
        phase: phase,
    });

    addLogMessage(`${getPhaseLabel(phase)} を開始します...`, 'info');
}

/**
 * ユーザーのアクションを送信
 */
function sendAction(action) {
    if (action === 'S') {
        openSkipModal();
        return;
    }

    wsManager.send({
        type: 'action',
        action: action,
    });

    // 指摘カードを非表示
    document.getElementById('issue-card').style.display = 'none';

    addLogMessage(`アクションを送信: [${action}]`, 'info');
}

function openSkipModal() {
    const modalElement = document.getElementById('skipModal');
    skipModalInstance = bootstrap.Modal.getOrCreateInstance(modalElement, {
        backdrop: 'static',
        keyboard: false,
    });

    document.getElementById('skip-item-input').value = '';
    document.getElementById('skip-item-input').classList.remove('is-invalid');
    document.getElementById('skip-reason-input').value = '';

    skipModalInstance.show();
}

function handleSkipSubmit() {
    const itemInput = document.getElementById('skip-item-input');
    const reasonInput = document.getElementById('skip-reason-input');

    const checklistItem = itemInput.value.trim();
    const reason = reasonInput.value.trim();

    if (!checklistItem) {
        itemInput.classList.add('is-invalid');
        addLogMessage('チェックリスト項目名を入力してください', 'error');
        return;
    }

    if (skipModalInstance) {
        skipModalInstance.hide();
    }

    wsManager.send({
        type: 'action',
        action: 'S',
        payload: {
            checklist_item: checklistItem,
            reason: reason,
        },
    });

    document.getElementById('issue-card').style.display = 'none';
    addLogMessage(`除外項目を送信: ${checklistItem}`, 'info');
}

/**
 * WebSocketメッセージを処理
 */
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'phase_start':
            addLogMessage(`${getPhaseLabel(data.phase)} を開始しました`, 'info');
            break;

        case 'iteration_start':
            updateIteration(data.iteration);
            addLogMessage(`イテレーション ${data.iteration} を開始`, 'info');
            break;

        case 'llm_response':
            addLogMessage('LLMから応答を受信しました', 'success');
            break;

        case 'issue_detected':
            displayIssue(data.issue, data.issue_number, data.total_issues);
            break;

        case 'action_received':
            addLogMessage(`アクション処理中: [${data.action}]`, 'info');
            break;

        case 'phase_complete':
            addLogMessage(`${getPhaseLabel(data.phase)} が完了しました`, 'success');
            hideStatusCard();
            enablePhaseButtons();
            AppState.isRunning = false;
            loadIterations(AppState.selectedPaperId);
            loadSessions(AppState.selectedPaperId); // セッションを再読み込み
            break;

        case 'embedded_error':
            // Phase2で埋め込まれた誤りを表示
            if (data.error) {
                addLogMessage(`誤り ${data.index}/${data.total}: ${data.error.checklist_item} - ${data.error.category}`, 'info');
            }
            break;

        case 'error':
            addLogMessage(`エラー: ${data.message}`, 'error');
            hideStatusCard();
            enablePhaseButtons();
            AppState.isRunning = false;
            break;

        case 'log':
            addLogMessage(data.message, data.level || 'info');
            break;

        case 'user_choice_required':
            handleUserChoice(data.message, data.choices);
            break;

        default:
            console.log('未処理のメッセージタイプ:', data.type);
    }
}

/**
 * ユーザー選択を処理
 */
async function handleUserChoice(message, choices) {
    // モーダルにメッセージを設定
    document.getElementById('user-choice-message').textContent = message;

    // モーダルを表示
    const modal = new bootstrap.Modal(document.getElementById('userChoiceModal'));
    modal.show();

    addLogMessage(`確認待ち: ${message}`, 'warning');

    // ボタンのイベントリスナーを設定（一度だけ実行）
    const yesBtn = document.getElementById('user-choice-yes');
    const noBtn = document.getElementById('user-choice-no');

    const handleYes = () => {
        modal.hide();
        sendUserChoice(choices[0]);
        yesBtn.removeEventListener('click', handleYes);
        noBtn.removeEventListener('click', handleNo);
    };

    const handleNo = () => {
        modal.hide();
        sendUserChoice(choices[1]);
        yesBtn.removeEventListener('click', handleYes);
        noBtn.removeEventListener('click', handleNo);
    };

    yesBtn.addEventListener('click', handleYes);
    noBtn.addEventListener('click', handleNo);
}

/**
 * ユーザー選択をサーバーに送信
 */
function sendUserChoice(choice) {
    wsManager.send({
        type: 'action',
        action: choice,
    });

    addLogMessage(`選択: ${choice}`, 'info');
}

/**
 * 指摘を表示
 */
function displayIssue(issue, issueNumber, totalIssues) {
    AppState.currentIssue = issue;

    document.getElementById('issue-number').textContent = issueNumber;
    document.getElementById('total-issues').textContent = totalIssues;
    document.getElementById('issue-before').textContent = issue.before;
    document.getElementById('issue-reasoning').textContent = issue.reasoning;
    document.getElementById('issue-after').textContent = issue.after;

    document.getElementById('issue-card').style.display = 'block';
    document.getElementById('issue-card').classList.add('fade-in');

    addLogMessage(`指摘 ${issueNumber}/${totalIssues} を表示`, 'warning');
}

/**
 * ステータスカードを表示
 */
function showStatusCard(phase) {
    document.getElementById('current-paper-id').textContent = AppState.selectedPaperId;
    document.getElementById('current-phase').textContent = getPhaseLabel(phase);
    document.getElementById('current-iteration').textContent = '0';
    document.getElementById('status-card').style.display = 'block';
}

/**
 * ステータスカードを非表示
 */
function hideStatusCard() {
    document.getElementById('status-card').style.display = 'none';
}

/**
 * イテレーション番号を更新
 */
function updateIteration(iteration) {
    document.getElementById('current-iteration').textContent = iteration;
}

/**
 * フェーズボタンを無効化
 */
function disablePhaseButtons() {
    document.getElementById('phase1-btn').disabled = true;
    document.getElementById('phase2-btn').disabled = true;
    document.getElementById('phase3-btn').disabled = true;
}

/**
 * フェーズボタンを有効化
 */
function enablePhaseButtons() {
    if (AppState.selectedPaperId) {
        document.getElementById('phase1-btn').disabled = false;
        document.getElementById('phase2-btn').disabled = false;
        document.getElementById('phase3-btn').disabled = false;
    }
}

/**
 * ログメッセージを追加
 */
function addLogMessage(message, level = 'info') {
    const logOutput = document.getElementById('log-output');
    const timestamp = new Date().toLocaleTimeString();

    const logClass = `log-${level}`;
    const logEntry = document.createElement('p');
    logEntry.className = 'mb-1';
    logEntry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span><span class="${logClass}">${message}</span>`;

    logOutput.appendChild(logEntry);
    logOutput.scrollTop = logOutput.scrollHeight;
}

/**
 * イテレーション履歴を読み込み
 */
async function loadIterations(paperId) {
    try {
        const data = await API.getIterations(paperId);
        displayIterations(data.iterations);
    } catch (error) {
        console.error('イテレーション履歴の読み込みエラー:', error);
    }
}

/**
 * イテレーション履歴を表示
 */
function displayIterations(iterations) {
    const tbody = document.querySelector('#iterations-table tbody');

    if (iterations.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    履歴データがありません
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = iterations.map(iter => `
        <tr>
            <td>${iter.paper_id}</td>
            <td><span class="badge bg-primary">${iter.phase}</span></td>
            <td>${iter.iteration}</td>
            <td>${iter.new_issues_count || 0}</td>
            <td><code>${iter.llm_model}</code></td>
            <td><small>${iter.timestamp}</small></td>
        </tr>
    `).join('');
}

/**
 * 設定を読み込み
 */
async function loadSettings() {
    try {
        const config = await API.getConfig();
        const settings = config.settings;

        document.getElementById('proofreading-provider').value =
            settings.llm.proofreading.provider;
        document.getElementById('proofreading-model').value =
            settings.llm.proofreading.model;
        document.getElementById('embedding-provider').value =
            settings.llm.embedding.provider;
        document.getElementById('embedding-model').value =
            settings.llm.embedding.model;
    } catch (error) {
        addLogMessage('設定の読み込みエラー: ' + error.message, 'error');
    }
}

/**
 * 設定を保存
 */
async function saveSettings() {
    try {
        const settings = {
            llm: {
                proofreading: {
                    provider: document.getElementById('proofreading-provider').value,
                    model: document.getElementById('proofreading-model').value,
                },
                embedding: {
                    provider: document.getElementById('embedding-provider').value,
                    model: document.getElementById('embedding-model').value,
                },
            },
        };

        await API.updateSettings(settings);

        addLogMessage('設定を保存しました', 'success');

        // モーダルを閉じる
        const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
        modal.hide();
    } catch (error) {
        addLogMessage('設定の保存エラー: ' + error.message, 'error');
    }
}

/**
 * セッション一覧を読み込み
 */
async function loadSessions(paperId) {
    try {
        const data = await API.getSessions(paperId);
        displaySessions(paperId, data.sessions);
    } catch (error) {
        console.error('セッション一覧の読み込みエラー:', error);
        addLogMessage('セッション一覧の読み込みに失敗しました', 'error');
    }
}

/**
 * セッション一覧を表示
 */
function displaySessions(paperId, sessions) {
    document.getElementById('sessions-paper-id').textContent = paperId;
    document.getElementById('sessions-card').style.display = 'block';

    const tbody = document.getElementById('sessions-tbody');

    if (sessions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    セッションがありません。Phase1を実行して新しいセッションを作成してください。
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = sessions.map(session => {
        const phase1Badge = session.phase1_complete
            ? '<span class="badge bg-success"><i class="bi bi-check-circle"></i> 完了</span>'
            : '<span class="badge bg-secondary">未実行</span>';

        const phase2Badge = session.phase2_complete
            ? '<span class="badge bg-success"><i class="bi bi-check-circle"></i> 完了</span>'
            : '<span class="badge bg-secondary">未実行</span>';

        const phase3Badge = session.phase3_complete
            ? '<span class="badge bg-success"><i class="bi bi-check-circle"></i> 完了</span>'
            : '<span class="badge bg-secondary">未実行</span>';

        const detectionRate = session.phase3_complete
            ? '<button class="btn btn-sm btn-outline-primary" onclick="loadDetectionRates(\'' + paperId + '\', \'' + session.session_id + '\')">表示</button>'
            : '<span class="text-muted">-</span>';

        return `
            <tr>
                <td><code>${session.session_id}</code></td>
                <td>${phase1Badge}</td>
                <td>${phase2Badge}</td>
                <td>${phase3Badge}</td>
                <td>${detectionRate}</td>
                <td>
                    <small class="text-muted">${new Date(session.phase1_start).toLocaleString('ja-JP')}</small>
                </td>
            </tr>
        `;
    }).join('');

    addLogMessage(`${sessions.length}件のセッションを表示しました`, 'info');
}

/**
 * 検出率を読み込み
 */
async function loadDetectionRates(paperId, sessionId) {
    try {
        addLogMessage(`検出率を計算中: セッション ${sessionId}`, 'info');

        const data = await API.getDetectionRates(paperId, sessionId);
        displayDetectionRates(data);

        addLogMessage(`検出率の計算が完了しました`, 'success');
    } catch (error) {
        console.error('検出率の読み込みエラー:', error);
        addLogMessage('検出率の読み込みに失敗しました: ' + error.message, 'error');
    }
}

/**
 * 検出率を表示
 */
function displayDetectionRates(data) {
    document.getElementById('detection-rates-card').style.display = 'block';

    // 全体統計
    document.getElementById('total-embedded').textContent = data.total_embedded;
    document.getElementById('total-detected').textContent = data.total_detected;
    document.getElementById('detection-rate').textContent = data.detection_rate.toFixed(1) + '%';

    // 項目別検出状況
    const tbody = document.getElementById('items-detection-tbody');

    if (!data.items_detection || Object.keys(data.items_detection).length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted">
                    データがありません
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = Object.entries(data.items_detection).map(([item, info]) => {
        const itemRate = info.total_count > 0
            ? ((info.detected_count / info.total_count) * 100).toFixed(1)
            : '0.0';

        const iterationText = info.first_detected_iteration > 0
            ? info.first_detected_iteration
            : '<span class="text-muted">未検出</span>';

        const rowClass = info.detected_count === info.total_count
            ? 'table-success'
            : info.detected_count > 0
            ? 'table-warning'
            : '';

        return `
            <tr class="${rowClass}">
                <td><code>${item}</code></td>
                <td>${info.detected_count} / ${info.total_count}</td>
                <td><strong>${itemRate}%</strong></td>
                <td>${iterationText}</td>
            </tr>
        `;
    }).join('');

    // 検出率カードまでスクロール
    document.getElementById('detection-rates-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * フェーズラベルを取得
 */
function getPhaseLabel(phase) {
    const labels = {
        phase1: 'フェーズ1: クリーン化',
        phase2: 'フェーズ2: エラー埋め込み',
        phase3: 'フェーズ3: 校正',
    };
    return labels[phase] || phase;
}

/**
 * データリセットを実行
 */
async function handleReset() {
    const resetResults = document.getElementById('reset-results').checked;
    const resetVersions = document.getElementById('reset-versions').checked;
    const resetProgress = document.getElementById('reset-progress').checked;

    if (!resetResults && !resetVersions && !resetProgress) {
        addLogMessage('削除する項目を選択してください', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reset_results: resetResults,
                reset_versions: resetVersions,
                reset_progress: resetProgress,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // モーダルを閉じる
        const modal = bootstrap.Modal.getInstance(document.getElementById('resetModal'));
        modal.hide();

        addLogMessage('データを削除しました', 'success');

        // UIを更新
        if (AppState.selectedPaperId) {
            loadIterations(AppState.selectedPaperId);
            loadSessions(AppState.selectedPaperId);
        }
    } catch (error) {
        console.error('リセットエラー:', error);
        addLogMessage(`リセットに失敗しました: ${error.message}`, 'error');
    }
}

/**
 * テキストをクリップボードにコピー
 */
async function copyToClipboard(elementId, buttonId) {
    const element = document.getElementById(elementId);
    const button = document.getElementById(buttonId);

    if (!element || !button) {
        console.error('Element not found:', elementId, buttonId);
        return;
    }

    const text = element.textContent;

    try {
        await navigator.clipboard.writeText(text);

        // ボタンのアイコンとテキストを一時的に変更
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="bi bi-check-circle-fill"></i> コピー完了！';
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-primary', 'btn-outline-success');

        // 1.5秒後に元に戻す
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('btn-success');
            if (elementId === 'issue-before') {
                button.classList.add('btn-outline-primary');
            } else {
                button.classList.add('btn-outline-success');
            }
        }, 1500);

        addLogMessage('クリップボードにコピーしました', 'success');
    } catch (err) {
        console.error('クリップボードへのコピーに失敗:', err);
        addLogMessage('クリップボードへのコピーに失敗しました', 'error');
    }
}
