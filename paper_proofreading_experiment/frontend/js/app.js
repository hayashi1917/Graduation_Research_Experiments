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

    // 設定保存
    document.getElementById('settings-save-btn').addEventListener('click', saveSettings);

    // アップロードボタン
    document.getElementById('upload-submit-btn').addEventListener('click', handleUpload);

    // フェーズボタン
    document.getElementById('phase1-btn').addEventListener('click', () => startPhase('phase1'));
    document.getElementById('phase2-btn').addEventListener('click', () => startPhase('phase2'));
    document.getElementById('phase3-btn').addEventListener('click', () => startPhase('phase3'));

    // 指摘判断ボタン
    document.getElementById('action-auto').addEventListener('click', () => sendAction('A'));
    document.getElementById('action-manual').addEventListener('click', () => sendAction('M'));
    document.getElementById('action-skip').addEventListener('click', () => sendAction('S'));
    document.getElementById('action-difficult').addEventListener('click', () => sendAction('D'));
    document.getElementById('action-quit').addEventListener('click', () => sendAction('Q'));

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
            <small>PDF: ${paper.pdf}</small><br>
            <small>TeX: ${paper.tex}</small>
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
function selectPaper(paperId) {
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

    // イテレーション履歴を読み込み
    loadIterations(paperId);
}

/**
 * 論文をアップロード
 */
async function handleUpload() {
    const paperId = document.getElementById('paper-id-input').value;
    const pdfFile = document.getElementById('pdf-file-input').files[0];
    const texFile = document.getElementById('tex-file-input').files[0];

    if (!paperId || !pdfFile || !texFile) {
        alert('すべての項目を入力してください');
        return;
    }

    try {
        addLogMessage(`論文をアップロード中: ${paperId}`, 'info');

        const result = await API.uploadPaper(paperId, pdfFile, texFile);

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
    wsManager.send({
        type: 'action',
        action: action,
    });

    // 指摘カードを非表示
    document.getElementById('issue-card').style.display = 'none';

    addLogMessage(`アクションを送信: [${action}]`, 'info');
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
    // シンプルなconfirmダイアログを使用
    const confirmed = confirm(message);
    const choice = confirmed ? choices[0] : choices[1];

    // 選択をサーバーに送信
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
            settings.llm.error_embedding.provider;
        document.getElementById('embedding-model').value =
            settings.llm.error_embedding.model;
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
                error_embedding: {
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
