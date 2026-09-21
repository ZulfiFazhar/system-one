(function () {
    // Preset Data
    const PRESETS = {
        billing: {
            state: 'User: "I was charged twice for my subscription on March 15th ($49 x 2). Please refund the duplicate transaction immediately."',
            questions: {
                is_refund: {
                    type: "noul",
                    instructions: "Is the user requesting a refund?",
                },
                category: {
                    type: "choice",
                    instructions: "Classify the support ticket category",
                    criteria: {
                        billing: "Payment, invoice, charge, or refund issues",
                        technical: "Software bugs, downtime, or performance errors",
                        account: "Login, password reset, or profile management",
                    },
                },
                urgency: {
                    type: "score",
                    instructions: "Rate customer urgency level",
                    criteria: [
                        "Low: General inquiry or informational request",
                        "Medium: Moderate issue without financial impact",
                        "High: Financial loss, duplicate charge, or blocked account",
                        "Critical: Security breach or system-wide disruption",
                    ],
                },
            },
        },
        outage: {
            state: "Alert: Production PostgreSQL cluster primary node unreachable. Replica promotion failed with timeout error 504. API error rate spiked to 84%.",
            questions: {
                requires_pager: {
                    type: "noul",
                    instructions: "Does this alert require paging on-call engineering?",
                },
                severity: {
                    type: "choice",
                    instructions: "Determine the incident severity level",
                    criteria: {
                        sev1: "Critical customer-facing system outage",
                        sev2: "Major component failure with partial degradation",
                        sev3: "Minor performance anomaly within SLA bounds",
                    },
                },
                priority_score: {
                    type: "score",
                    instructions: "Calculated response priority",
                    criteria: [
                        "P4: Routine scheduled maintenance",
                        "P3: Non-urgent investigation required",
                        "P2: Urgent engineering response needed",
                        "P1: Immediate emergency response required",
                    ],
                },
            },
        },
        sales: {
            state: "Prospect: \"We currently run 240 engineers on legacy infrastructure. We want to adopt System One for real-time automated decisions across all our microservices.\"",
            questions: {
                is_enterprise: {
                    type: "noul",
                    instructions: "Is this an enterprise scale opportunity?",
                },
                sales_segment: {
                    type: "choice",
                    instructions: "Assign to sales qualification tier",
                    criteria: {
                        enterprise: "Strategic enterprise accounts with 100+ seats",
                        midmarket: "Growth companies with 20-99 seats",
                        startup: "Early stage teams and self-serve plans",
                    },
                },
                expansion_score: {
                    type: "score",
                    instructions: "Assess account expansion potential",
                    criteria: [
                        "Tier C: Standard volume usage",
                        "Tier B: Strong team growth potential",
                        "Tier A: High-value strategic expansion target",
                    ],
                },
            },
        },
    };

    let currentPresetKey = "billing";

    // DOM Elements
    const apiKeyInput = document.getElementById("api-key-input");
    const openrouterKeyInput = document.getElementById("openrouter-key-input");
    const stateInput = document.getElementById("state-input");
    const questionsInput = document.getElementById("questions-input");
    const runBtn = document.getElementById("run-btn");
    const runSpinner = document.getElementById("run-spinner");
    const runText = document.getElementById("run-text");
    const errorBox = document.getElementById("playground-error");
    const errorTitle = document.getElementById("error-title");
    const errorMessage = document.getElementById("error-message");
    const resStatus = document.getElementById("res-status");
    const resLatency = document.getElementById("res-latency");
    const resTokens = document.getElementById("res-tokens");
    const tabVisual = document.getElementById("tab-visual");
    const tabCompare = document.getElementById("tab-compare");
    const tabRaw = document.getElementById("tab-raw");
    const visualResults = document.getElementById("visual-results");
    const compareResults = document.getElementById("compare-results");
    const compareEmpty = document.getElementById("compare-empty");
    const compareContent = document.getElementById("compare-content");
    const compareCards = document.getElementById("compare-cards");
    const compareLayaLatency = document.getElementById("compare-laya-latency");
    const compareJevLatency = document.getElementById("compare-jev-latency");
    const rawResults = document.getElementById("raw-results");
    const resultsEmpty = document.getElementById("results-empty");
    const resultsContent = document.getElementById("results-content");
    const rawJson = document.getElementById("raw-json");
    const copyCurlBtn = document.getElementById("copy-curl-btn");
    const resetQuestionsBtn = document.getElementById("reset-questions-btn");
    const healthDot = document.getElementById("health-dot");
    const healthText = document.getElementById("health-text");

    let activeTab = "visual"; // "visual" | "compare" | "raw"

    // Session Storage for API Keys
    const STORAGE_KEY = "system_one_api_key";
    const OPENROUTER_STORAGE_KEY = "openrouter_api_key";

    const savedApiKey = sessionStorage.getItem(STORAGE_KEY);
    if (savedApiKey) {
        apiKeyInput.value = savedApiKey;
    }
    apiKeyInput.addEventListener("input", function () {
        const val = apiKeyInput.value.trim();
        if (val) {
            sessionStorage.setItem(STORAGE_KEY, val);
        } else {
            sessionStorage.removeItem(STORAGE_KEY);
        }
    });

    if (openrouterKeyInput) {
        const savedORKey = sessionStorage.getItem(OPENROUTER_STORAGE_KEY);
        if (savedORKey) {
            openrouterKeyInput.value = savedORKey;
        }
        openrouterKeyInput.addEventListener("input", function () {
            const val = openrouterKeyInput.value.trim();
            if (val) {
                sessionStorage.setItem(OPENROUTER_STORAGE_KEY, val);
            } else {
                sessionStorage.removeItem(OPENROUTER_STORAGE_KEY);
            }
        });
    }

    // Load Preset Function
    function loadPreset(key) {
        currentPresetKey = key;
        const preset = PRESETS[key];
        if (!preset) return;
        stateInput.value = preset.state;
        questionsInput.value = JSON.stringify(preset.questions, null, 2);
        hideError();
    }

    // Preset Button Event Listeners
    document
        .getElementById("preset-billing")
        .addEventListener("click", function () {
            loadPreset("billing");
        });
    document
        .getElementById("preset-outage")
        .addEventListener("click", function () {
            loadPreset("outage");
        });
    document
        .getElementById("preset-sales")
        .addEventListener("click", function () {
            loadPreset("sales");
        });

    // Reset Questions Button
    resetQuestionsBtn.addEventListener("click", function () {
        const preset = PRESETS[currentPresetKey];
        if (preset) {
            questionsInput.value = JSON.stringify(preset.questions, null, 2);
        }
    });

    // Tab Switching
    function setTab(tab) {
        activeTab = tab;
        const activeClass = "px-2.5 py-1 bg-white text-black font-semibold";
        const inactiveClass = "px-2.5 py-1 bg-[#18181b] text-zinc-400 hover:bg-[#27272a]";

        tabVisual.className = tab === "visual" ? activeClass : inactiveClass;
        if (tabCompare) tabCompare.className = tab === "compare" ? activeClass : inactiveClass;
        tabRaw.className = tab === "raw" ? activeClass : inactiveClass;

        visualResults.classList.toggle("hidden", tab !== "visual");
        if (compareResults) compareResults.classList.toggle("hidden", tab !== "compare");
        rawResults.classList.toggle("hidden", tab !== "raw");
    }

    tabVisual.addEventListener("click", function () {
        setTab("visual");
    });

    if (tabCompare) {
        tabCompare.addEventListener("click", function () {
            setTab("compare");
        });
    }

    tabRaw.addEventListener("click", function () {
        setTab("raw");
    });

    // Error Display Helpers
    function showError(title, msg) {
        errorTitle.textContent = title;
        errorMessage.textContent = msg;
        errorBox.classList.remove("hidden");
    }

    function hideError() {
        errorBox.classList.add("hidden");
    }

    // Health Polling
    async function pollHealth() {
        const mobileDot = document.getElementById("mobile-health-dot");
        const mobileText = document.getElementById("mobile-health-text");
        try {
            const resp = await fetch("/health");
            if (resp.ok) {
                const data = await resp.json();
                if (data.status === "ready") {
                    if (healthDot) healthDot.className = "w-2 h-2 rounded-full bg-emerald-400 inline-block live-pulse";
                    if (healthText) healthText.textContent = "Model Ready: " + (data.model || "laya");
                    if (mobileDot) mobileDot.className = "w-2 h-2 rounded-full bg-emerald-400 inline-block live-pulse";
                    if (mobileText) mobileText.textContent = "Ready";
                } else {
                    if (healthDot) healthDot.className = "w-2 h-2 rounded-full bg-yellow-400 inline-block";
                    if (healthText) healthText.textContent = "Status: " + data.status;
                    if (mobileDot) mobileDot.className = "w-2 h-2 rounded-full bg-yellow-400 inline-block";
                    if (mobileText) mobileText.textContent = "Wait";
                }
            } else {
                if (healthDot) healthDot.className = "w-2 h-2 rounded-full bg-red-500 inline-block";
                if (healthText) healthText.textContent = "Health HTTP " + resp.status;
                if (mobileDot) mobileDot.className = "w-2 h-2 rounded-full bg-red-500 inline-block";
                if (mobileText) mobileText.textContent = "Error";
            }
        } catch (e) {
            if (healthDot) healthDot.className = "w-2 h-2 rounded-full bg-red-500 inline-block";
            if (healthText) healthText.textContent = "Service Offline";
            if (mobileDot) mobileDot.className = "w-2 h-2 rounded-full bg-red-500 inline-block";
            if (mobileText) mobileText.textContent = "Offline";
        }
    }

    pollHealth();
    setInterval(pollHealth, 10000);

    // Copy cURL Button
    copyCurlBtn.addEventListener("click", function () {
        const curlText = document.getElementById("curl-code").innerText;
        navigator.clipboard
            .writeText(curlText)
            .then(function () {
                const originalText = copyCurlBtn.textContent;
                copyCurlBtn.textContent = "Copied!";
                setTimeout(function () {
                    copyCurlBtn.textContent = originalText;
                }, 2000);
            })
            .catch(function () {
                copyCurlBtn.textContent = "Failed";
                setTimeout(function () {
                    copyCurlBtn.textContent = "Copy cURL";
                }, 2000);
            });
    });

    // Render Answer Card Helper
    function renderAnswerCard(key, ans) {
        const card = document.createElement("div");
        card.className = "border border-[#27272a] p-4 bg-[#141417] text-white shadow-hard";

        const header = document.createElement("div");
        header.className = "flex items-center justify-between mb-3 border-b border-zinc-800 pb-2";

        const titleSpan = document.createElement("span");
        titleSpan.className = "font-mono font-bold text-sm text-white";
        titleSpan.textContent = key;

        const typeSpan = document.createElement("span");
        typeSpan.className = "text-xs font-mono px-2 py-0.5 border border-[#3f3f46] bg-[#18181b] text-zinc-300";
        typeSpan.textContent = ans.type;

        header.appendChild(titleSpan);
        header.appendChild(typeSpan);
        card.appendChild(header);

        if (ans.type === "noul") {
            const prob = typeof ans.noul === "number" ? ans.noul : 0;
            const pct = (prob * 100).toFixed(1);
            const isTrue = prob >= 0.5;

            const content = document.createElement("div");
            content.className = "space-y-2";

            const verdictRow = document.createElement("div");
            verdictRow.className = "flex items-center justify-between text-sm";
            const probLabel = document.createElement("span");
            probLabel.className = "text-xs font-mono text-zinc-400";
            probLabel.textContent = "Probability:";
            const probVal = document.createElement("span");
            probVal.className = "font-mono font-bold text-sm " + (isTrue ? "text-emerald-400" : "text-zinc-200");
            probVal.textContent = pct + "% (" + prob.toFixed(4) + ")";
            verdictRow.appendChild(probLabel);
            verdictRow.appendChild(probVal);
            content.appendChild(verdictRow);

            const progressBg = document.createElement("div");
            progressBg.className = "w-full h-3 bg-[#0c0c0e] border border-[#27272a] overflow-hidden";
            const progressFill = document.createElement("div");
            progressFill.className = "h-full progress-bar-fill " + (isTrue ? "bg-emerald-500" : "bg-zinc-600");
            progressFill.style.width = "0%";
            progressBg.appendChild(progressFill);
            content.appendChild(progressBg);
            requestAnimationFrame(function () {
                setTimeout(function () {
                    progressFill.style.width = pct + "%";
                }, 50);
            });

            card.appendChild(content);
        } else if (ans.type === "choice") {
            const chosen = ans.choice || "";
            const conf = typeof ans.confidence === "number" ? (ans.confidence * 100).toFixed(1) : "0.0";

            const content = document.createElement("div");
            content.className = "space-y-3";

            const choiceRow = document.createElement("div");
            choiceRow.className = "flex items-center justify-between text-sm";
            const choiceLabel = document.createElement("span");
            choiceLabel.className = "text-xs font-mono text-zinc-400";
            choiceLabel.textContent = "Selected Choice:";
            const choiceVal = document.createElement("span");
            choiceVal.className = "font-mono font-bold px-2 py-0.5 border border-pink-500/40 bg-pink-950/40 text-pink-300";
            choiceVal.textContent = chosen + " (" + conf + "% conf)";
            choiceRow.appendChild(choiceLabel);
            choiceRow.appendChild(choiceVal);
            content.appendChild(choiceRow);

            if (ans.probabilities && typeof ans.probabilities === "object") {
                const probContainer = document.createElement("div");
                probContainer.className = "space-y-1.5 pt-1";

                for (const optKey in ans.probabilities) {
                    const optProb = ans.probabilities[optKey];
                    const optPct = (optProb * 100).toFixed(1);
                    const isChosen = optKey === chosen;

                    const row = document.createElement("div");
                    row.className = "space-y-0.5";

                    const labelRow = document.createElement("div");
                    labelRow.className = "flex justify-between text-xs font-mono " + (isChosen ? "font-bold text-white" : "text-zinc-400");
                    const keySpan = document.createElement("span");
                    keySpan.textContent = optKey;
                    const pctSpan = document.createElement("span");
                    pctSpan.textContent = optPct + "%";
                    labelRow.appendChild(keySpan);
                    labelRow.appendChild(pctSpan);
                    row.appendChild(labelRow);

                    const barBg = document.createElement("div");
                    barBg.className = "w-full h-2 bg-[#0c0c0e] border border-zinc-800 overflow-hidden";
                    const barFill = document.createElement("div");
                    barFill.className = "h-full progress-bar-fill " + (isChosen ? "bg-white" : "bg-zinc-700");
                    barFill.style.width = "0%";
                    barBg.appendChild(barFill);
                    row.appendChild(barBg);
                    (function (bf, targetPct) {
                        requestAnimationFrame(function () {
                            setTimeout(function () {
                                bf.style.width = targetPct + "%";
                            }, 50);
                        });
                    })(barFill, optPct);

                    probContainer.appendChild(row);
                }
                content.appendChild(probContainer);
            }

            card.appendChild(content);
        } else if (ans.type === "score") {
            const score = typeof ans.score === "number" ? ans.score.toFixed(2) : "0";
            const conf = typeof ans.confidence === "number" ? (ans.confidence * 100).toFixed(1) : "0.0";

            const content = document.createElement("div");
            content.className = "space-y-3";

            const scoreRow = document.createElement("div");
            scoreRow.className = "flex items-center justify-between text-sm";
            const scoreLabel = document.createElement("span");
            scoreLabel.className = "text-xs font-mono text-zinc-400";
            scoreLabel.textContent = "Calculated Score:";
            const scoreVal = document.createElement("span");
            scoreVal.className = "font-mono font-bold text-base px-2 py-0.5 border border-cyan-500/40 bg-cyan-950/40 text-cyan-300";
            scoreVal.textContent = score + " (" + conf + "% conf)";
            scoreRow.appendChild(scoreLabel);
            scoreRow.appendChild(scoreVal);
            content.appendChild(scoreRow);

            if (ans.probabilities && typeof ans.probabilities === "object") {
                const probContainer = document.createElement("div");
                probContainer.className = "space-y-1.5 pt-1";

                for (const optKey in ans.probabilities) {
                    const optProb = ans.probabilities[optKey];
                    const optPct = (optProb * 100).toFixed(1);
                    const legendDesc = ans.legend && ans.legend[optKey] ? ans.legend[optKey] : optKey;

                    const row = document.createElement("div");
                    row.className = "space-y-0.5";

                    const labelRow = document.createElement("div");
                    labelRow.className = "flex justify-between text-xs font-mono text-zinc-400";
                    const descSpan = document.createElement("span");
                    descSpan.title = String(legendDesc);
                    descSpan.textContent = String(legendDesc);
                    const pctSpan = document.createElement("span");
                    pctSpan.textContent = optPct + "%";
                    labelRow.appendChild(descSpan);
                    labelRow.appendChild(pctSpan);
                    row.appendChild(labelRow);

                    const barBg = document.createElement("div");
                    barBg.className = "w-full h-2 bg-[#0c0c0e] border border-zinc-800 overflow-hidden";
                    const barFill = document.createElement("div");
                    barFill.className = "h-full bg-cyan-400 progress-bar-fill";
                    barFill.style.width = "0%";
                    barBg.appendChild(barFill);
                    row.appendChild(barBg);
                    (function (bf, targetPct) {
                        requestAnimationFrame(function () {
                            setTimeout(function () {
                                bf.style.width = targetPct + "%";
                            }, 50);
                        });
                    })(barFill, optPct);

                    probContainer.appendChild(row);
                }
                content.appendChild(probContainer);
            }

            card.appendChild(content);
        }

        return card;
    }

    function renderModelAnswerDetails(container, ans) {
        if (!ans) {
            const na = document.createElement("div");
            na.className = "text-zinc-500 italic text-[11px]";
            na.textContent = "No answer returned";
            container.appendChild(na);
            return;
        }

        if (ans.type === "noul") {
            const prob = typeof ans.noul === "number" ? ans.noul : 0;
            const pct = (prob * 100).toFixed(1);
            const row = document.createElement("div");
            row.className = "flex items-center justify-between text-xs";
            row.innerHTML = `<span class="text-zinc-400">Probability:</span><span class="font-bold text-white font-mono">${pct}% (${prob.toFixed(4)})</span>`;
            container.appendChild(row);

            const barBg = document.createElement("div");
            barBg.className = "w-full h-1.5 bg-zinc-900 border border-zinc-800 overflow-hidden mt-1";
            const barFill = document.createElement("div");
            barFill.className = "h-full bg-cyan-400 progress-bar-fill";
            barFill.style.width = pct + "%";
            barBg.appendChild(barFill);
            container.appendChild(barBg);
        } else if (ans.type === "choice") {
            const chosen = ans.choice || "";
            const conf = typeof ans.confidence === "number" ? (ans.confidence * 100).toFixed(1) : "0.0";
            const row = document.createElement("div");
            row.className = "flex items-center justify-between text-xs";
            row.innerHTML = `<span class="text-zinc-400">Choice:</span><span class="font-bold text-white font-mono px-1.5 py-0.5 border border-[#3f3f46] bg-[#18181b]">${chosen} (${conf}%)</span>`;
            container.appendChild(row);

            if (ans.probabilities && typeof ans.probabilities === "object") {
                const probList = document.createElement("div");
                probList.className = "space-y-1 pt-1.5";
                for (const k in ans.probabilities) {
                    const p = ans.probabilities[k];
                    const pct = (p * 100).toFixed(1);
                    const isChosen = k === chosen;
                    const item = document.createElement("div");
                    item.className = "flex justify-between text-[11px] font-mono " + (isChosen ? "text-white font-bold" : "text-zinc-400");
                    item.innerHTML = `<span>${k}${isChosen ? " &#10003;" : ""}:</span><span>${pct}%</span>`;
                    probList.appendChild(item);
                }
                container.appendChild(probList);
            }
        } else if (ans.type === "score") {
            const score = typeof ans.score === "number" ? ans.score.toFixed(2) : "0";
            const conf = typeof ans.confidence === "number" ? (ans.confidence * 100).toFixed(1) : "0.0";
            const row = document.createElement("div");
            row.className = "flex items-center justify-between text-xs";
            row.innerHTML = `<span class="text-zinc-400">Score:</span><span class="font-bold text-white font-mono">${score} (${conf}%)</span>`;
            container.appendChild(row);

            if (ans.probabilities && typeof ans.probabilities === "object") {
                const probList = document.createElement("div");
                probList.className = "space-y-1 pt-1.5";
                for (const k in ans.probabilities) {
                    const p = ans.probabilities[k];
                    const pct = (p * 100).toFixed(1);
                    const label = (ans.legend && ans.legend[k]) ? ans.legend[k] : k;
                    const item = document.createElement("div");
                    item.className = "flex justify-between text-[11px] font-mono text-zinc-400";
                    item.innerHTML = `<span>${label}:</span><span>${pct}%</span>`;
                    probList.appendChild(item);
                }
                container.appendChild(probList);
            }
        }
    }

    function renderCompareResults(layaData, jevData, layaElapsed, jevElapsed) {
        if (compareLayaLatency) compareLayaLatency.textContent = "Latency: " + layaElapsed + " ms";
        if (compareJevLatency) compareJevLatency.textContent = "Latency: " + jevElapsed + " ms";

        if (!compareCards) return;
        compareCards.innerHTML = "";

        const layaAnswers = layaData.answers || {};
        const jevAnswers = jevData.answers || {};
        const allKeys = Array.from(new Set([...Object.keys(layaAnswers), ...Object.keys(jevAnswers)]));

        if (allKeys.length === 0) {
            compareCards.innerHTML = '<div class="text-xs font-mono text-zinc-500 italic p-4 text-center">No questions evaluated.</div>';
            return;
        }

        for (const qKey of allKeys) {
            const layaAns = layaAnswers[qKey];
            const jevAns = jevAnswers[qKey];

            const card = document.createElement("div");
            card.className = "border border-[#27272a] p-4 bg-[#141417] text-white shadow-hard";

            const header = document.createElement("div");
            header.className = "flex flex-wrap items-center justify-between gap-2 mb-3 border-b border-zinc-800 pb-2";

            const titleDiv = document.createElement("div");
            titleDiv.className = "flex items-center gap-2";
            const keySpan = document.createElement("span");
            keySpan.className = "font-mono font-bold text-sm text-white";
            keySpan.textContent = qKey;
            const typeSpan = document.createElement("span");
            typeSpan.className = "text-xs font-mono px-2 py-0.5 border border-[#3f3f46] bg-[#18181b] text-zinc-300";
            typeSpan.textContent = (layaAns ? layaAns.type : (jevAns ? jevAns.type : "unknown"));
            titleDiv.appendChild(keySpan);
            titleDiv.appendChild(typeSpan);

            // Calculate Agreement Badge
            const agreeBadge = document.createElement("span");
            agreeBadge.className = "text-xs font-mono px-2 py-0.5 border";

            let isMatch = false;
            if (layaAns && jevAns && layaAns.type === jevAns.type) {
                if (layaAns.type === "choice") {
                    isMatch = layaAns.choice === jevAns.choice;
                } else if (layaAns.type === "noul") {
                    isMatch = Math.abs((layaAns.noul || 0) - (jevAns.noul || 0)) <= 0.25;
                } else if (layaAns.type === "score") {
                    isMatch = Math.abs((layaAns.score || 0) - (jevAns.score || 0)) <= 0.6;
                }
            }

            if (isMatch) {
                agreeBadge.className += " border-emerald-500/40 bg-emerald-950/40 text-emerald-400";
                agreeBadge.textContent = "Consensus Match";
            } else {
                agreeBadge.className += " border-yellow-500/40 bg-yellow-950/40 text-yellow-300";
                agreeBadge.textContent = "Divergent Decision";
            }

            header.appendChild(titleDiv);
            header.appendChild(agreeBadge);
            card.appendChild(header);

            // Comparison columns: Laya vs Jev
            const grid = document.createElement("div");
            grid.className = "grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono";

            const layaCol = document.createElement("div");
            layaCol.className = "p-3 border border-[#27272a] bg-[#0c0c0e] space-y-2";
            const layaTitle = document.createElement("div");
            layaTitle.className = "font-bold text-cyan-400 text-xs flex items-center justify-between border-b border-zinc-800 pb-1";
            layaTitle.innerHTML = "<span>Laya Multilingual (Local)</span>";
            layaCol.appendChild(layaTitle);
            renderModelAnswerDetails(layaCol, layaAns);

            const jevCol = document.createElement("div");
            jevCol.className = "p-3 border border-[#27272a] bg-[#0c0c0e] space-y-2";
            const jevTitle = document.createElement("div");
            jevTitle.className = "font-bold text-pink-400 text-xs flex items-center justify-between border-b border-zinc-800 pb-1";
            jevTitle.innerHTML = "<span>TypeSafe Jev (OpenRouter)</span>";
            jevCol.appendChild(jevTitle);
            renderModelAnswerDetails(jevCol, jevAns);

            grid.appendChild(layaCol);
            grid.appendChild(jevCol);
            card.appendChild(grid);

            compareCards.appendChild(card);
        }

        if (compareEmpty) compareEmpty.classList.add("hidden");
        if (compareContent) compareContent.classList.remove("hidden");
    }

    // Run Evaluation Handler
    runBtn.addEventListener("click", async function () {
        hideError();

        const stateText = stateInput.value.trim();
        if (!stateText) {
            showError("Input Validation", "Please enter a state context string.");
            return;
        }

        let parsedQuestions = {};
        try {
            parsedQuestions = JSON.parse(questionsInput.value);
            if (typeof parsedQuestions !== "object" || parsedQuestions === null || Object.keys(parsedQuestions).length === 0) {
                showError("Schema Validation", "Questions schema must be a non-empty JSON object mapping IDs to questions.");
                return;
            }
        } catch (jsonErr) {
            showError("JSON Syntax Error", "Failed to parse questions schema: " + jsonErr.message);
            return;
        }

        const isCompare = (activeTab === "compare");
        const openrouterKey = openrouterKeyInput ? openrouterKeyInput.value.trim() : "";

        if (isCompare && !openrouterKey) {
            showError(
                "OpenRouter Key Required",
                "Please enter your OpenRouter API key in the field on the left to benchmark against typesafe/jev-1.13."
            );
            if (openrouterKeyInput) openrouterKeyInput.focus();
            return;
        }

        runBtn.disabled = true;
        runSpinner.classList.remove("hidden");
        runText.textContent = isCompare ? "Running Comparison..." : "Evaluating...";

        const payload = {
            state: stateText,
            model: "laya",
            questions: parsedQuestions,
        };

        const headers = {
            "Content-Type": "application/json",
        };
        const enteredApiKey = apiKeyInput.value.trim();
        if (enteredApiKey) {
            headers["Authorization"] = "Bearer " + enteredApiKey;
        }

        const startTime = performance.now();

        try {
            // Step 1: Execute Laya call on this server (strictly checks rate limit)
            const response = await fetch("/v1/systemone", {
                method: "POST",
                headers: headers,
                body: JSON.stringify(payload),
            });

            const elapsedMs = Math.round(performance.now() - startTime);
            resLatency.textContent = elapsedMs + " ms";
            resLatency.classList.remove("hidden");

            if (!response.ok) {
                resStatus.className = "text-xs font-mono px-2 py-0.5 border border-red-500/40 bg-red-950/40 text-red-300";
                let errDetail = "HTTP " + response.status;
                try {
                    const errJson = await response.json();
                    errDetail = JSON.stringify(errJson, null, 2);
                } catch (err) {
                    errDetail = await response.text();
                }
                showError("Laya Inference Failed (" + response.status + ")", errDetail);
                rawJson.textContent = errDetail;
                // If Laya rate limits or fails, halt immediately (no comparison shown)
                return;
            }

            resStatus.className = "text-xs font-mono px-2 py-0.5 border border-emerald-500/40 bg-emerald-950/40 text-emerald-400";
            resStatus.textContent = "200 OK";
            resStatus.classList.remove("hidden");

            const layaData = await response.json();

            // Update token usage
            if (layaData.usage) {
                resTokens.textContent = "in: " + (layaData.usage.input_tokens || 0) + " / out: " + (layaData.usage.output_tokens || 0) + " tok";
                resTokens.classList.remove("hidden");
            }

            // Update visual cards for Laya
            resultsContent.innerHTML = "";
            if (layaData.answers && typeof layaData.answers === "object") {
                for (const qKey in layaData.answers) {
                    const card = renderAnswerCard(qKey, layaData.answers[qKey]);
                    resultsContent.appendChild(card);
                }
                resultsEmpty.classList.add("hidden");
                resultsContent.classList.remove("hidden");
            }

            // Step 2: If in Compare mode, query OpenRouter Decisions API directly from browser
            if (isCompare) {
                const jevStartTime = performance.now();
                let jevResponse;
                try {
                    jevResponse = await fetch("https://openrouter.ai/api/alpha/decisions", {
                        method: "POST",
                        headers: {
                            "Authorization": "Bearer " + openrouterKey,
                            "Content-Type": "application/json",
                            "HTTP-Referer": window.location.origin,
                            "X-Title": "System One Benchmark",
                        },
                        body: JSON.stringify({
                            model: "typesafe/jev-1.13",
                            state: stateText,
                            questions: parsedQuestions,
                        }),
                    });
                } catch (netErr) {
                    showError("OpenRouter Network Error", "Could not connect to OpenRouter: " + netErr.message);
                    return;
                }

                const jevElapsedMs = Math.round(performance.now() - jevStartTime);

                if (!jevResponse.ok) {
                    let jevErr = "HTTP " + jevResponse.status;
                    try {
                        const errJson = await jevResponse.json();
                        jevErr = JSON.stringify(errJson, null, 2);
                    } catch (e) {
                        jevErr = await jevResponse.text();
                    }
                    showError("OpenRouter Jev Error (" + jevResponse.status + ")", jevErr);
                    return;
                }

                const jevData = await jevResponse.json();

                // Update raw JSON view with both models
                rawJson.textContent = JSON.stringify({
                    laya_local: layaData,
                    typesafe_jev_openrouter: jevData,
                }, null, 2);

                // Render side by side comparison
                renderCompareResults(layaData, jevData, elapsedMs, jevElapsedMs);
            } else {
                rawJson.textContent = JSON.stringify(layaData, null, 2);
            }

        } catch (netErr) {
            const elapsedMs = Math.round(performance.now() - startTime);
            resLatency.textContent = elapsedMs + " ms";
            resLatency.classList.remove("hidden");
            showError("Network / Client Error", netErr.message || "Could not reach /v1/systemone");
        } finally {
            runBtn.disabled = false;
            runSpinner.classList.add("hidden");
            runText.textContent = "Run System 1 Evaluation";
        }
    });

    // Scroll Reveal Observer
    if ("IntersectionObserver" in window) {
        const scrollObserver = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("revealed");
                        scrollObserver.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.08,
                rootMargin: "0px 0px -40px 0px",
            }
        );
        document.querySelectorAll(".reveal-on-scroll").forEach(function (el) {
            scrollObserver.observe(el);
        });
    } else {
        document.querySelectorAll(".reveal-on-scroll").forEach(function (el) {
            el.classList.add("revealed");
        });
    }

    // Sync live domain/origin to code examples
    if (window.location && window.location.origin) {
        const liveEndpoint = window.location.origin + "/v1/systemone";
        document.querySelectorAll(".api-endpoint-url").forEach(function (el) {
            el.textContent = liveEndpoint;
        });
    }

    // Mobile Navigation Drawer Toggle
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    const mobileMenu = document.getElementById("mobile-menu");
    const menuIconOpen = document.getElementById("menu-icon-open");
    const menuIconClose = document.getElementById("menu-icon-close");

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener("click", function () {
            const isClosed = mobileMenu.classList.contains("hidden");
            if (isClosed) {
                mobileMenu.classList.remove("hidden");
                mobileMenuBtn.setAttribute("aria-expanded", "true");
                if (menuIconOpen) menuIconOpen.classList.add("hidden");
                if (menuIconClose) menuIconClose.classList.remove("hidden");
            } else {
                mobileMenu.classList.add("hidden");
                mobileMenuBtn.setAttribute("aria-expanded", "false");
                if (menuIconOpen) menuIconOpen.classList.remove("hidden");
                if (menuIconClose) menuIconClose.classList.add("hidden");
            }
        });

        // Close menu on mobile link click
        document.querySelectorAll(".mobile-nav-link").forEach(function (link) {
            link.addEventListener("click", function () {
                mobileMenu.classList.add("hidden");
                mobileMenuBtn.setAttribute("aria-expanded", "false");
                if (menuIconOpen) menuIconOpen.classList.remove("hidden");
                if (menuIconClose) menuIconClose.classList.add("hidden");
            });
        });
    }

    // Initialize with default preset
    loadPreset("billing");
})();
