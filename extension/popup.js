/**
 * CP Coach Chrome Extension
 * Optimized for daily use with minimal friction
 * 
 * Features:
 * - UI State Machine (idle/loading/success/error/empty)
 * - Input debouncing (500ms)
 * - Request locking (prevents duplicate requests)
 * - Local caching of last successful analysis
 * - Handle format validation
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const API_BASE_URL = 'https://cp-coach-backend.onrender.com';
const API_V1_URL = `${API_BASE_URL}/api/v1`;  // New versioned API
const DEBOUNCE_DELAY = 500;  // ms
const HANDLE_PATTERN = /^[a-zA-Z0-9_-]{3,24}$/;

// =============================================================================
// UI STATE MACHINE
// =============================================================================

const UIState = {
    IDLE: 'idle',
    LOADING: 'loading',
    SUCCESS: 'success',
    ERROR: 'error',
    EMPTY: 'empty'
};

// Mode state: 'doing' | 'random' | null
let currentMode = null;

let currentUIState = UIState.IDLE;
let isRequestPending = false;  // Prevents duplicate requests
let debounceTimer = null;

// =============================================================================
// DOM ELEMENTS
// =============================================================================

const handleInput = document.getElementById('handle');
const handleStatus = document.getElementById('handle-status');
const topicSelect = document.getElementById('topic');
const nextButton = document.getElementById('next-problem');
const resultSection = document.getElementById('result');
const loadingEl = document.getElementById('loading');
const errorEl = document.getElementById('error');
const problemEl = document.getElementById('problem');
const problemName = document.getElementById('problem-name');
const problemRating = document.getElementById('problem-rating');
const problemExplanation = document.getElementById('problem-explanation');
const solveLink = document.getElementById('solve-link');
const skipBtn = document.getElementById('skip-btn');
const markSolvedBtn = document.getElementById('mark-solved');
const solvedStatus = document.getElementById('solved-status');
const dailyCounter = document.getElementById('daily-counter');

// Timer Elements
const timerDisplay = document.getElementById('timer-display');
const timerToggle = document.getElementById('timer-toggle');
const timerPause = document.getElementById('timer-pause');
let timerInterval = null;
let timerSeconds = 0;
let timerState = {
    isRunning: false,
    startTime: null,
    accumulated: 0
};

// Analysis Elements
const viewAnalysisBtn = document.getElementById('view-analysis');
const analysisView = document.getElementById('analysis-view');
const analysisLoading = document.getElementById('analysis-loading');
const analysisContent = document.getElementById('analysis-content');
const aiExplanation = document.getElementById('ai-explanation');
const weakBandsList = document.getElementById('weak-bands-list');
const weakTopicsList = document.getElementById('weak-topics-list');
const upsolveList = document.getElementById('upsolve-list');
const refreshUpsolveBtn = document.getElementById('refresh-upsolve');
const backToHomeBtn = document.getElementById('back-to-home');
const inputSection = document.querySelector('.input-section');

// Mode Selection Elements
const modeSection = document.getElementById('mode-selection');
const modeDoingBtn = document.getElementById('mode-doing');
const modeRandomBtn = document.getElementById('mode-random');
const changeModeBtn = document.getElementById('change-mode');

// Current problem data
let currentProblem = null;

// Detected problem from URL (for Doing mode)
let detectedProblem = null;

// =============================================================================
// VALIDATION & UTILITIES
// =============================================================================

/**
 * Validate CF handle format
 */
function validateHandle(handle) {
    if (!handle) return { valid: false, error: 'Handle cannot be empty' };
    if (handle.length < 3) return { valid: false, error: 'Handle too short (min 3 chars)' };
    if (handle.length > 24) return { valid: false, error: 'Handle too long (max 24 chars)' };
    if (!HANDLE_PATTERN.test(handle)) {
        return { valid: false, error: 'Invalid characters in handle' };
    }
    return { valid: true, error: null };
}

/**
 * Debounce function
 */
function debounce(func, delay) {
    return function (...args) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * Set UI state with appropriate rendering
 */
function setUIState(state, data = {}) {
    currentUIState = state;

    resultSection.classList.remove('hidden');
    loadingEl.classList.add('hidden');
    errorEl.classList.add('hidden');
    problemEl.classList.add('hidden');

    switch (state) {
        case UIState.IDLE:
            resultSection.classList.add('hidden');
            resetButton();
            break;

        case UIState.LOADING:
            loadingEl.classList.remove('hidden');
            // Show skeleton instead of just spinner
            loadingEl.innerHTML = `
                <div class="skeleton-loader">
                    <div class="skeleton-line skeleton-title"></div>
                    <div class="skeleton-line skeleton-rating"></div>
                    <div class="skeleton-line skeleton-text"></div>
                </div>
            `;
            nextButton.disabled = true;
            nextButton.textContent = 'Finding...';
            break;

        case UIState.SUCCESS:
            problemEl.classList.remove('hidden');
            resetButton();
            break;

        case UIState.ERROR:
            errorEl.classList.remove('hidden');
            errorEl.innerHTML = `
                <div class="error-message">
                    <span>${data.message || 'An error occurred'}</span>
                    ${data.retryable ? '<button class="retry-btn" onclick="retryLastRequest()">Retry</button>' : ''}
                </div>
            `;
            resetButton();
            break;

        case UIState.EMPTY:
            errorEl.classList.remove('hidden');
            errorEl.textContent = data.message || 'No problems found';
            resetButton();
            break;
    }
}

// Store last request for retry
let lastRequestParams = null;

function retryLastRequest() {
    if (lastRequestParams) {
        fetchRecommendation(lastRequestParams.handle, lastRequestParams.topic);
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

// Add listener for refresh button
if (refreshUpsolveBtn) {
    refreshUpsolveBtn.addEventListener('click', () => {
        refreshUpsolveBtn.style.transform = 'rotate(360deg)';
        setTimeout(() => refreshUpsolveBtn.style.transform = '', 500);
        fetchAnalysis(true);
    });
}

// Rating adjustment buttons
const ratingLowerBtn = document.getElementById('rating-lower');
const ratingHigherBtn = document.getElementById('rating-higher');
let userRatingOffset = 0;

// Load rating offset and cached data on startup
(async function initializeExtension() {
    const stored = await chrome.storage.sync.get(['ratingOffset']);
    if (stored.ratingOffset !== undefined) {
        userRatingOffset = stored.ratingOffset;
    }

    // Load cached analysis for instant display
    const cachedAnalysis = await chrome.storage.local.get(['lastAnalysis']);
    if (cachedAnalysis.lastAnalysis) {
        // Analysis is cached, can be shown instantly on reopen
    }
})();

// Rating adjustment handlers with validation
if (ratingLowerBtn) {
    ratingLowerBtn.addEventListener('click', async () => {
        userRatingOffset -= 100;
        await chrome.storage.sync.set({ ratingOffset: userRatingOffset });
        const handle = handleInput.value.trim();
        const topic = topicSelect.value;
        if (handle && !isRequestPending) {
            await fetchRecommendation(handle, topic);
        }
    });
}

if (ratingHigherBtn) {
    ratingHigherBtn.addEventListener('click', async () => {
        userRatingOffset += 100;
        await chrome.storage.sync.set({ ratingOffset: userRatingOffset });
        const handle = handleInput.value.trim();
        const topic = topicSelect.value;
        if (handle && !isRequestPending) {
            await fetchRecommendation(handle, topic);
        }
    });
}

// Handle input validation with debounce
if (handleInput) {
    handleInput.addEventListener('input', debounce(async () => {
        const handle = handleInput.value.trim();
        const validation = validateHandle(handle);

        if (!handle) {
            handleStatus.textContent = '';
            handleStatus.className = '';
        } else if (!validation.valid) {
            handleStatus.textContent = '✗ ' + validation.error;
            handleStatus.className = 'status-error';
        } else {
            handleStatus.textContent = '✓ Valid format';
            handleStatus.className = 'status-ok';
        }
    }, DEBOUNCE_DELAY));
}

/**
 * Initialize popup on load
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Load saved mode
    const stored = await chrome.storage.sync.get(['selectedMode', 'lastTopic', 'currentProblem', 'cfHandle']);

    if (stored.selectedMode) {
        // User has previously selected a mode
        currentMode = stored.selectedMode;
        await initializeMode(currentMode);
    } else {
        // Show mode selection screen
        showModeSelection();
    }

    if (stored.lastTopic) {
        topicSelect.value = stored.lastTopic;
    }

    // Restore current problem instantly from cache (only for random mode)
    if (stored.currentProblem && currentMode === 'random') {
        currentProblem = stored.currentProblem;
        displayProblem(currentProblem, stored.currentProblem.targetRating || 0);
    }

    restoreTimerState();
});

/**
 * Show mode selection screen
 */
function showModeSelection() {
    modeSection.classList.remove('hidden');
    inputSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    analysisView.classList.add('hidden');
    changeModeBtn.classList.add('hidden');
}

/**
 * Initialize the selected mode
 */
async function initializeMode(mode) {
    currentMode = mode;
    await chrome.storage.sync.set({ selectedMode: mode });

    modeSection.classList.add('hidden');
    changeModeBtn.classList.remove('hidden');

    if (mode === 'doing') {
        await initializeDoingMode();
    } else {
        await initializeRandomMode();
    }
}

/**
 * Initialize Doing Mode - auto-detect problem from active tab
 */
async function initializeDoingMode() {
    // Hide topic selector in doing mode
    inputSection.classList.remove('hidden');
    topicSelect.parentElement.classList.add('hidden');
    viewAnalysisBtn.classList.add('hidden');

    // Update button text
    nextButton.textContent = 'FIND SIMILAR';

    // Try to detect problem from active tab
    await tryAutoDetectHandle();
    await tryAutoDetectProblem();
}

/**
 * Initialize Random Mode - standard behavior
 */
async function initializeRandomMode() {
    inputSection.classList.remove('hidden');
    topicSelect.parentElement.classList.remove('hidden');
    viewAnalysisBtn.classList.remove('hidden');

    nextButton.textContent = 'FIND PROBLEM';

    await tryAutoDetectHandle();
}

/**
 * Try to auto-detect Codeforces problem from active tab URL
 * Patterns: 
 * - https://codeforces.com/problemset/problem/{contestId}/{index}
 * - https://codeforces.com/contest/{contestId}/problem/{index}
 */
async function tryAutoDetectProblem() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        if (tab && tab.url) {
            // Match problemset pattern
            let match = tab.url.match(/codeforces\.com\/problemset\/problem\/(\d+)\/([A-Za-z0-9]+)/);

            // Match contest pattern
            if (!match) {
                match = tab.url.match(/codeforces\.com\/contest\/(\d+)\/problem\/([A-Za-z0-9]+)/);
            }

            if (match) {
                const contestId = match[1];
                const index = match[2].toUpperCase();

                // Fetch problem details from Codeforces API
                await fetchAndDisplayDetectedProblem(contestId, index);
                return;
            }
        }
    } catch (e) {
        console.error("Problem detection failed", e);
    }

    // No problem detected - show message
    showError('Open a Codeforces problem page to auto-detect, or click "Find Similar" to get recommendations based on your history.');
}

/**
 * Fetch problem details from Codeforces and display
 */
async function fetchAndDisplayDetectedProblem(contestId, index) {
    showLoading();

    try {
        // Fetch from CF API
        const res = await fetch(`https://codeforces.com/api/problemset.problems`);
        if (!res.ok) throw new Error('Failed to fetch from Codeforces');

        const data = await res.json();
        if (data.status !== 'OK') throw new Error('Codeforces API error');

        // Find the specific problem
        const problem = data.result.problems.find(
            p => p.contestId == contestId && p.index === index
        );

        if (problem) {
            detectedProblem = {
                id: null, // Not from our DB
                contestId: problem.contestId,
                index: problem.index,
                name: `${problem.contestId}${problem.index}. ${problem.name}`,
                rating: problem.rating || 'Unrated',
                tags: problem.tags || [],
                url: `https://codeforces.com/problemset/problem/${problem.contestId}/${problem.index}`,
                explanation: `Tags: ${problem.tags.join(', ') || 'None'}`
            };

            currentProblem = detectedProblem;
            displayProblem(detectedProblem);
        } else {
            showError('Problem not found in Codeforces database');
        }
    } catch (error) {
        showError('Failed to fetch problem details: ' + error.message);
    }
}

// Mode button event listeners
if (modeDoingBtn) {
    modeDoingBtn.addEventListener('click', () => initializeMode('doing'));
}

if (modeRandomBtn) {
    modeRandomBtn.addEventListener('click', () => initializeMode('random'));
}

if (changeModeBtn) {
    changeModeBtn.addEventListener('click', async () => {
        // Clear saved mode and show selection
        await chrome.storage.sync.remove('selectedMode');
        currentMode = null;
        showModeSelection();
    });
}

/**
 * TASK 1: Auto-detect Codeforces handle from active tab URL
 * Pattern: https://codeforces.com/profile/<handle>
 */
async function tryAutoDetectHandle() {
    try {
        // Get active tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        if (tab && tab.url) {
            // Check if on Codeforces profile page
            const match = tab.url.match(/codeforces\.com\/profile\/([a-zA-Z0-9_-]+)/);

            if (match) {
                const detectedHandle = match[1];
                handleInput.value = detectedHandle;
                handleStatus.textContent = '✓ Auto-detected';

                // Save to storage
                await chrome.storage.sync.set({ cfHandle: detectedHandle });

                // Fetch user status (daily count) immediately
                await fetchUserStatus(detectedHandle);
                return;
            }
        }
    } catch (e) {
        // Tab access might fail, continue to fallback
    }

    // Fallback: Load from storage
    const stored = await chrome.storage.sync.get(['cfHandle']);
    if (stored.cfHandle) {
        handleInput.value = stored.cfHandle;
        handleStatus.textContent = '✓ Remembered';

        // Fetch user status (daily count) immediately
        await fetchUserStatus(stored.cfHandle);
    }
}

/**
 * Fetch User Status (Daily Count)
 */
async function fetchUserStatus(handle) {
    try {
        const res = await fetch(`${API_BASE_URL}/user/${handle}`);
        if (res.ok) {
            const data = await res.json();
            if (data.daily_solved_count !== undefined) {
                dailyCounter.textContent = `Daily: ${data.daily_solved_count}`;
                dailyCounter.classList.remove('hidden');
            }
        }
    } catch (e) {
        console.error("Status fetch failed", e);
        // Don't hide it, keep previous value or --
    }
}

/**
 * TASK 2: Save topic when changed
 */
topicSelect.addEventListener('change', async () => {
    await chrome.storage.sync.set({ lastTopic: topicSelect.value });
});

/**
 * TASK 3: "FIND PROBLEM" / "FIND SIMILAR" primary flow
 */
nextButton.addEventListener('click', async () => {
    const handle = handleInput.value.trim();

    // Validate handle
    if (!handle) {
        showError('Open a Codeforces profile or enter your handle');
        return;
    }

    // Save handle for next time
    await chrome.storage.sync.set({ cfHandle: handle });

    // Fetch user status
    fetchUserStatus(handle);

    if (currentMode === 'doing') {
        // Doing mode: find similar problems based on detected problem's tags
        if (detectedProblem && detectedProblem.tags && detectedProblem.tags.length > 0) {
            // Use the first tag from the detected problem
            const primaryTag = detectedProblem.tags[0];
            await chrome.storage.sync.set({ lastTopic: primaryTag });
            await fetchRecommendation(handle, primaryTag);
        } else {
            // No detected problem or no tags - try to detect again
            await tryAutoDetectProblem();
        }
    } else {
        // Random mode: use selected topic
        const topic = topicSelect.value;
        await chrome.storage.sync.set({ lastTopic: topic });
        await fetchRecommendation(handle, topic);
    }
});

/**
 * Fetch recommendation from backend
 */
async function fetchRecommendation(handle, topic) {
    showLoading();
    solvedStatus.classList.add('hidden');

    try {
        // Ensure user exists in backend
        const userRes = await fetch(`${API_BASE_URL}/user/${encodeURIComponent(handle)}`);
        if (!userRes.ok) {
            let errMsg = 'User not found on Codeforces';
            try {
                const err = await userRes.json();
                errMsg = err.detail || errMsg;
            } catch (e) {
                // Response not JSON, use default message
            }
            throw new Error(errMsg);
        }

        // Fetch recommendation (include rating offset if set)
        let url = `${API_BASE_URL}/extension/recommend?handle=${encodeURIComponent(handle)}&topic=${encodeURIComponent(topic)}`;
        if (userRatingOffset !== 0) {
            url += `&rating_offset=${userRatingOffset}`;
        }
        const res = await fetch(url);

        if (!res.ok) {
            let errMsg = 'Failed to get recommendations';
            try {
                const err = await res.json();
                errMsg = err.detail || errMsg;
            } catch (e) {
                // Response not JSON, use default message
            }
            throw new Error(errMsg);
        }

        const data = await res.json();

        // Handle empty results
        if (!data.problems || data.problems.length === 0) {
            showError(data.message || 'No problems found for this topic');
            // Clear stored problem when no results
            await chrome.storage.sync.remove('currentProblem');
            currentProblem = null;
            return;
        }

        // Display first problem and save to storage
        const problem = data.problems[0];
        problem.targetRating = data.target_rating;
        if (data.daily_count !== undefined) {
            dailyCounter.textContent = `Daily: ${data.daily_count}`;
            dailyCounter.classList.remove('hidden');
        }

        displayProblem(data.problems[0], data.target_rating);

        // Save current problem to persist across popup reopens
        const problemToSave = {
            ...data.problems[0],
            targetRating: data.target_rating
        };
        await chrome.storage.sync.set({ currentProblem: problemToSave });

    } catch (error) {
        if (error.name === 'TypeError') {
            showError('Backend not reachable. Is the server running?');
        } else {
            showError(error.message);
        }
    }
}

/**
 * Display loading state
 */
function showLoading() {
    resultSection.classList.remove('hidden');
    loadingEl.classList.remove('hidden');
    errorEl.classList.add('hidden');
    problemEl.classList.add('hidden');
    nextButton.disabled = true;
    nextButton.textContent = 'Finding...';
}

/**
 * Display error message
 */
function showError(message) {
    resultSection.classList.remove('hidden');
    loadingEl.classList.add('hidden');
    errorEl.classList.remove('hidden');
    errorEl.textContent = message;
    problemEl.classList.add('hidden');
    resetButton();
}

/**
 * Display problem result
 */
function displayProblem(problem, targetRating) {
    resultSection.classList.remove('hidden');
    loadingEl.classList.add('hidden');
    errorEl.classList.add('hidden');
    problemEl.classList.remove('hidden');

    // Store for Mark as Solved
    currentProblem = problem;

    // Populate UI
    problemName.textContent = problem.name;
    problemRating.textContent = problem.rating;
    problemExplanation.textContent = problem.explanation;
    solveLink.href = problem.url;

    // Reset solved button
    markSolvedBtn.disabled = false;
    markSolvedBtn.textContent = 'Mark as Solved';
    solvedStatus.classList.add('hidden');

    resetButton();
    resetButton();
    resetTimer(); // Reset timer for new problem
}

if (timerToggle) {
    timerToggle.addEventListener('click', () => {
        if (timerState.isRunning) {
            // Stop/Reset? No, the main button should probably be "Start" / "Reset" 
            // and the separate button is Pause.
            // User asked for "Pause button".
            // Let's make: 
            // [Start] -> changes to [Reset] ?? 
            // Actually standard: [Start] -> [Stop] (Resets). Pause is separate.
            // But user said "do something else the timer resets... make sure it started even if closed".

            // Logic:
            // Toggle Button: Starts if stopped. Resets if running?
            // Let's stick to: Toggle = Start / Stop (Reset).
            // Pause = Pause / Resume.

            // Wait, standard UI:
            // [Start] -> [Pause] [Reset]

            // Let's implement:
            // Toggle Button: "Start" (if stopped) / "Reset" (if running/paused).
            // Pause Button: "Pause" (if running) / "Resume" (if paused).

            // Actually simpler implementation requested: "Start timer... pause button".
            // Button 1: Start / Reset
            // Button 2: Pause / Resume (visible only when started)

            if (timerState.isRunning || timerState.accumulated > 0) {
                // It's active. This button acts as RESET now?
                // Or acts as Stop?
                resetTimer();
            } else {
                startTimer();
            }
        } else {
            if (timerState.accumulated > 0) {
                // Paused state -> This button resets
                resetTimer();
            } else {
                startTimer();
            }
        }
    });
}

if (timerPause) {
    timerPause.addEventListener('click', () => {
        if (timerState.isRunning) {
            pauseTimer();
        } else {
            resumeTimer();
        }
    });
}


// Persist Logic
async function saveTimerState() {
    await chrome.storage.local.set({ 'timerState': timerState });
}

async function restoreTimerState() {
    const data = await chrome.storage.local.get(['timerState']);
    if (data.timerState) {
        timerState = data.timerState;

        // Calculate elapsed if running
        if (timerState.isRunning && timerState.startTime) {
            const now = Date.now();
            const elapsedSinceStart = Math.floor((now - timerState.startTime) / 1000);
            timerSeconds = timerState.accumulated + elapsedSinceStart;

            // Restart interval
            startInterval();
        } else {
            // Just set accumulated
            timerSeconds = timerState.accumulated;
        }
        updateTimerUI();
    }
}

function startTimer() {
    timerState.isRunning = true;
    timerState.startTime = Date.now();
    // accumulated stays same (0 if fresh)
    saveTimerState();
    startInterval();
    updateTimerUI();
}

function pauseTimer() {
    // Calculate accumulated
    const now = Date.now();
    const elapsed = Math.floor((now - timerState.startTime) / 1000);
    timerState.accumulated += elapsed;
    timerState.startTime = null;
    timerState.isRunning = false;

    saveTimerState();
    clearInterval(timerInterval);
    timerSeconds = timerState.accumulated;
    updateTimerUI();
}

function resumeTimer() {
    timerState.isRunning = true;
    timerState.startTime = Date.now();
    saveTimerState();
    startInterval();
    updateTimerUI();
}

function startInterval() {
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        // Recalculate based on real time to prevent drift
        const now = Date.now();
        const currentElapsed = Math.floor((now - timerState.startTime) / 1000);
        timerSeconds = timerState.accumulated + currentElapsed;
        updateTimerUI();
    }, 1000);
}

function resetTimer() {
    clearInterval(timerInterval);
    timerState = {
        isRunning: false,
        startTime: null,
        accumulated: 0
    };
    timerSeconds = 0;
    saveTimerState();
    updateTimerUI();
}

function updateTimerUI() {
    const mins = Math.floor(timerSeconds / 60).toString().padStart(2, '0');
    const secs = (timerSeconds % 60).toString().padStart(2, '0');
    if (timerDisplay) timerDisplay.textContent = `${mins}:${secs}`;

    if (timerToggle) {
        if (timerState.isRunning || timerState.accumulated > 0) {
            timerToggle.textContent = 'Reset';
            timerToggle.classList.add('active'); // Red style usually
        } else {
            timerToggle.textContent = 'Start Timer';
            timerToggle.classList.remove('active');
        }
    }

    if (timerPause) {
        if (timerState.isRunning || timerState.accumulated > 0) {
            timerPause.classList.remove('hidden');
            timerPause.textContent = timerState.isRunning ? 'Pause' : 'Resume';
        } else {
            timerPause.classList.add('hidden');
        }
    }
}

/**
 * Reset primary button
 */
function resetButton() {
    nextButton.disabled = false;
    nextButton.textContent = currentMode === 'doing' ? 'FIND SIMILAR' : 'FIND PROBLEM';
}

/**
 * TASK 4: Mark as Solved button - marks problem and auto-fetches next
 */
markSolvedBtn.addEventListener('click', async () => {
    if (!currentProblem) return;

    const handle = handleInput.value.trim();
    const topic = topicSelect.value;
    if (!handle) return;

    markSolvedBtn.disabled = true;
    markSolvedBtn.textContent = 'Saving...';

    try {
        // POST to backend /solve endpoint
        let url = `${API_BASE_URL}/solve/${currentProblem.id}?handle=${encodeURIComponent(handle)}&verdict=AC`;

        // Add time if used (and non-zero)
        if (timerSeconds > 0) {
            url += `&time_taken=${timerSeconds}`;
        }

        const res = await fetch(url, { method: 'POST' });

        if (!res.ok) {
            throw new Error('Failed to mark as solved');
        }

        const data = await res.json();

        // Clear stored problem (and timer)
        await chrome.storage.sync.remove('currentProblem');
        resetTimer();
        currentProblem = null;

        // Check for AI advice (Too Slow)
        if (data.ai_analysis && data.ai_analysis.is_slow && data.ai_analysis.advice) {
            alert(`⚠️ Coach's Insight:\n\nThat took a bit longer than expected for this rating.\n\nTip: ${data.ai_analysis.advice}`);
        }

        // Show brief success, then auto-fetch next problem
        markSolvedBtn.textContent = '✓ Marked!';
        solvedStatus.textContent = 'Fetching next problem...';
        solvedStatus.classList.remove('hidden');

        // Small delay to show feedback, then fetch next
        setTimeout(async () => {
            await fetchRecommendation(handle, topic);
        }, 500);

    } catch (error) {
        markSolvedBtn.textContent = 'Error';
        setTimeout(() => {
            markSolvedBtn.disabled = false;
            markSolvedBtn.textContent = 'Mark as Solved';
        }, 2000);
    }
});

/**
 * Skip button - record skip to backend, then fetch next problem
 * Backend tracks skip count and auto-marks as solved on 2nd skip
 */
skipBtn.addEventListener('click', async () => {
    const handle = handleInput.value.trim();
    const topic = topicSelect.value;

    if (!handle || !currentProblem) return;

    skipBtn.disabled = true;
    skipBtn.textContent = 'Skipping...';

    try {
        // Or simpler: We assume users skip mostly because it's too hard unless they say otherwise?

        // Let's use `confirm("Was this problem TOO EASY for you?")`
        // YES -> too_easy -> +100
        // NO -> We assume it was "Boring" or "Too Hard".
        // Let's try a double confirm? No that's annoying.

        // BEST MVP: Just Ask "Is this problem TOO EASY?"
        let feedback = null;
        if (confirm("Is this problem TOO EASY for you?\n\nClick OK for 'Too Easy' (I'll increase difficulty).\nClick Cancel for 'Too Hard/Boring' (I'll decrease/maintain difficulty).")) {
            feedback = "too_easy";
        } else {
            feedback = "too_hard";
        }

        // Call skip API endpoint
        const url = `${API_BASE_URL}/skip/${currentProblem.id}?handle=${encodeURIComponent(handle)}&feedback=${feedback}`;
        const res = await fetch(url, { method: 'POST' });

        if (!res.ok) {
            throw new Error('Failed to record skip');
        }

        const data = await res.json();

        // Clear stored problem
        await chrome.storage.sync.remove('currentProblem');
        currentProblem = null;

        // Show feedback if auto-marked as solved
        if (data.auto_solved) {
            solvedStatus.textContent = 'Skipped twice — marked as solved!';
            if (data.daily_count !== undefined) {
                dailyCounter.textContent = `Daily: ${data.daily_count}`;
                dailyCounter.classList.remove('hidden');
            }
            solvedStatus.classList.remove('hidden');
        }

        // Fetch next recommendation
        await fetchRecommendation(handle, topic);

    } catch (error) {
        skipBtn.textContent = 'Error';
        setTimeout(() => {
            skipBtn.disabled = false;
            skipBtn.textContent = 'Skip';
        }, 2000);
    } finally {
        skipBtn.disabled = false;
        skipBtn.textContent = 'Skip';
    }
});

/**
 * TASK 5: Analysis View Logic
 */

// Toggle between Main and Analysis views
viewAnalysisBtn.addEventListener('click', async () => {
    const handle = handleInput.value.trim();
    if (!handle) {
        showError('Please enter a handle first');
        return;
    }

    // Switch views
    inputSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    analysisView.classList.remove('hidden');

    // Fetch data
    await fetchAnalysis();
});

backToHomeBtn.addEventListener('click', () => {
    analysisView.classList.add('hidden');
    inputSection.classList.remove('hidden');
    // Don't auto-show result section, let user click Find Problem
});

/**
 * Fetch Weakness Analysis
 */
async function fetchAnalysis(refresh = false) {
    const handle = handleInput.value.trim();
    if (!handle) return;

    // Only show loading full screen if NOT refreshing (refresh is subtle)
    if (!refresh) {
        analysisLoading.classList.remove('hidden');
        analysisContent.classList.add('hidden');
    } else {
        // For refresh, maybe just dim opacity or show small spinner?
        // For now, keep it simple: UI is responsive enough
        upsolveList.style.opacity = '0.5';
    }

    try {
        let url = `${API_BASE_URL}/analysis/weaknesses?handle=${handle}`;
        if (refresh) {
            url += `&refresh=true`;
        }

        const res = await fetch(url);

        if (!res.ok) {
            throw new Error('Failed to fetch analysis');
        }

        const data = await res.json();

        if (refresh) {
            upsolveList.style.opacity = '1';
        }

        displayAnalysis(data);

    } catch (error) {
        aiExplanation.textContent = "Error loading analysis. Please try again.";
        analysisLoading.classList.add('hidden');
        analysisContent.classList.remove('hidden');
        if (refresh) upsolveList.style.opacity = '1';
    }
}

/**
 * Display Analysis Data
 */
function displayAnalysis(data) {
    analysisLoading.classList.add('hidden');
    analysisContent.classList.remove('hidden');

    // 1. AI Explanation
    if (data.summary_explanation && !data.summary_explanation.includes("Error")) {
        aiExplanation.textContent = data.summary_explanation;
    } else {
        aiExplanation.textContent = "AI insights unavailable at the moment. Focus on the data below.";
    }

    // 2. Weak Bands
    weakBandsList.innerHTML = '';
    if (data.weak_band_details && data.weak_band_details.length > 0) {
        data.weak_band_details.forEach(band => {
            const li = document.createElement('li');
            li.textContent = `${band.band} (${Math.round(band.unsolved_rate * 100)}% unsolved)`;
            weakBandsList.appendChild(li);
        });
    } else {
        weakBandsList.innerHTML = '<li>No significant weak rating bands detected</li>';
    }

    // 3. Weak Topics
    weakTopicsList.innerHTML = '';
    if (data.weak_topic_details && data.weak_topic_details.length > 0) {
        data.weak_topic_details.forEach(topic => {
            const li = document.createElement('li');
            li.textContent = `${topic.topic} (${Math.round(topic.solved_rate * 100)}% solve rate)`;
            weakTopicsList.appendChild(li);
        });
    } else {
        weakTopicsList.innerHTML = '<li>No significant weak topics detected</li>';
    }

    // 4. Upsolve Suggestions
    upsolveList.innerHTML = '';
    if (data.upsolve_suggestions && data.upsolve_suggestions.length > 0) {
        data.upsolve_suggestions.forEach(prob => {
            const card = document.createElement('div');
            card.className = 'upsolve-card';

            // Use URL provided by backend
            const probUrl = prob.url || '#';

            card.innerHTML = `
                <div class="upsolve-header" style="justify-content:space-between; display:flex;">
                    <div style="flex-grow:1; cursor:pointer;" class="upsolve-select-area">
                        <span class="upsolve-name">${prob.name}</span>
                        <span class="upsolve-rating" style="display:block; font-size:11px;">${prob.rating}</span>
                    </div>
                    <!-- Link button removed per user request -->
                </div>
                <div class="upsolve-reason">
                    ${prob.reason}
                </div>
                <button class="btn-primary upsolve-select-btn" style="width:100%; margin-top:8px; padding:6px; font-size:12px;">Select Problem</button>
            `;

            // Handle "Select Problem" click
            const selectBtn = card.querySelector('.upsolve-select-btn');
            selectBtn.addEventListener('click', async () => {
                // Switch to main view
                analysisView.classList.add('hidden');
                resultSection.classList.remove('hidden');

                // Construct problem object
                const selectedProblem = {
                    id: prob.db_id, // Might be null
                    name: prob.name,
                    rating: prob.rating,
                    explanation: "Upsolve Suggestion: " + prob.reason,
                    url: probUrl
                };

                // Display and save
                displayProblem(selectedProblem);
                await chrome.storage.sync.set({ currentProblem: selectedProblem });
            });

            upsolveList.appendChild(card);
        });
    } else {
        upsolveList.innerHTML = '<div class="upsolve-reason">No specific upsolve suggestions right now.</div>';
    }
}

/**
 * Update displayProblem to handle missing IDs
 */
const originalDisplayProblem = displayProblem;
displayProblem = function (problem, targetRating) {
    // Call original logic
    resultSection.classList.remove('hidden');
    loadingEl.classList.add('hidden');
    errorEl.classList.add('hidden');
    problemEl.classList.remove('hidden');

    currentProblem = problem;

    problemName.textContent = problem.name;
    problemRating.textContent = problem.rating;
    problemExplanation.textContent = problem.explanation;
    solveLink.href = problem.url;

    // Handle button state based on DB ID existence
    if (problem.id) {
        markSolvedBtn.disabled = false;
        markSolvedBtn.textContent = 'Mark as Solved';
        markSolvedBtn.title = "";

        skipBtn.disabled = false;
        skipBtn.textContent = 'Skip';
        skipBtn.title = "";
    } else {
        markSolvedBtn.disabled = true;
        markSolvedBtn.textContent = 'Untracked Problem';
        markSolvedBtn.title = "This problem is not in the local database and cannot be tracked.";

        skipBtn.disabled = true;
        skipBtn.textContent = 'Skip (N/A)';
        skipBtn.title = "This problem is not in the local database.";
    }

    solvedStatus.classList.add('hidden');

    // Reset find button
    nextButton.disabled = false;
    nextButton.textContent = currentMode === 'doing' ? 'FIND SIMILAR' : 'FIND PROBLEM';
};
