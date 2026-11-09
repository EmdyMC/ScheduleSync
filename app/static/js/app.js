// ==============================================================================
// ScheduleSync - Full-Stack Client Application (Dark Theme & Blue Accent)
// ==============================================================================

const API_BASE = window.SCHEDULESYNC_API_BASE || "/api";
let currentUser = null;
let activeTab = "heatmap";
let currentHeatmapData = null;
let currentTimetableData = null;
let myFriendsList = [];
let myGroupsList = [];

// Helper: HTTP Request with JWT Authorization
async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem("schedulesync_token");
    const headers = options.headers || {};
    
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            localStorage.removeItem("schedulesync_token");
            currentUser = null;
            renderAuthUI();
            throw new Error("Session expired. Please log in again.");
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || data.message || "An unexpected error occurred.");
        }
        return data;
    } catch (err) {
        console.error(`API Error [${endpoint}]:`, err);
        throw err;
    }
}

// Notification System (Clean, Professional, No Emojis)
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    const bgColors = {
        success: "bg-emerald-600 text-white",
        error: "bg-rose-600 text-white",
        info: "bg-blue-600 text-white",
        warning: "bg-amber-600 text-white"
    };

    toast.className = `px-4 py-2.5 rounded-lg shadow-xl flex items-center space-x-3 text-xs font-semibold transition-all transform duration-300 opacity-0 translate-y-2 border border-slate-700/50 ${bgColors[type] || bgColors.info}`;
    toast.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" class="ml-2 opacity-75 hover:opacity-100 focus:outline-none">&times;</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove("opacity-0", "translate-y-2");
    }, 10);

    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Authentication
async function initApp() {
    const token = localStorage.getItem("schedulesync_token");
    if (!token) {
        renderAuthUI();
        return;
    }

    try {
        const data = await apiRequest("/auth/me");
        currentUser = data.user;
        renderAppUI();
        loadInitialData();
    } catch (err) {
        renderAuthUI();
    }
}

function renderAuthUI() {
    document.getElementById("auth-modal").classList.remove("hidden");
    document.getElementById("app-dashboard").classList.add("hidden");
}

function renderAppUI() {
    document.getElementById("auth-modal").classList.add("hidden");
    document.getElementById("app-dashboard").classList.remove("hidden");

    if (currentUser) {
        document.getElementById("user-name-display").textContent = currentUser.full_name;
        document.getElementById("user-reg-display").textContent = currentUser.reg_no || `@${currentUser.username}`;
        document.getElementById("user-avatar-badge").style.backgroundColor = currentUser.avatar_color || "#2563eb";
        document.getElementById("user-avatar-badge").textContent = currentUser.full_name.charAt(0).toUpperCase();
    }
}

async function handleLogin(identifier, password) {
    try {
        const data = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({ username_or_email: identifier, password: password })
        });
        localStorage.setItem("schedulesync_token", data.access_token);
        currentUser = data.user;
        showToast(`Logged in as ${currentUser.full_name}.`);
        renderAppUI();
        loadInitialData();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleRegister(payload) {
    try {
        const data = await apiRequest("/auth/register", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        localStorage.setItem("schedulesync_token", data.access_token);
        currentUser = data.user;
        showToast("Account created successfully.");
        renderAppUI();
        loadInitialData();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function handleLogout() {
    localStorage.removeItem("schedulesync_token");
    currentUser = null;
    showToast("Logged out.", "info");
    renderAuthUI();
}

// Navigation Tabs
function switchTab(tabId) {
    activeTab = tabId;
    const tabs = ["heatmap", "timetable", "friends", "groups"];
    
    tabs.forEach(t => {
        const content = document.getElementById(`tab-content-${t}`);
        const navBtn = document.getElementById(`nav-tab-${t}`);
        if (content) {
            content.classList.toggle("hidden", t !== tabId);
        }
        if (navBtn) {
            if (t === tabId) {
                navBtn.className = "flex items-center space-x-2 px-3.5 py-2 rounded-lg font-bold bg-blue-600 text-white shadow transition-all text-xs";
            } else {
                navBtn.className = "flex items-center space-x-2 px-3.5 py-2 rounded-lg font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-all text-xs";
            }
        }
    });

    if (tabId === "heatmap") loadHeatmapControls();
    if (tabId === "timetable") loadMyTimetable();
    if (tabId === "friends") loadFriendsHub();
    if (tabId === "groups") loadGroupsHub();
}

async function loadInitialData() {
    switchTab("heatmap");
}

// ==============================================================================
// TAB 1: Heatmap (Faithful to Original Matplotlib Palette & Layout)
// ==============================================================================

// Original 5-stop color gradient from main.py
// ["#e04b4b", "#f2a93c", "#f5d76e", "#8fd35c", "#3fb950"]
function hexToRgb(hex) {
    const c = hex.replace("#", "");
    return [
        parseInt(c.substring(0, 2), 16),
        parseInt(c.substring(2, 4), 16),
        parseInt(c.substring(4, 6), 16)
    ];
}

function interpolateColors(color1, color2, factor) {
    const rgb1 = hexToRgb(color1);
    const rgb2 = hexToRgb(color2);
    const r = Math.round(rgb1[0] + factor * (rgb2[0] - rgb1[0]));
    const g = Math.round(rgb1[1] + factor * (rgb2[1] - rgb1[1]));
    const b = Math.round(rgb1[2] + factor * (rgb2[2] - rgb1[2]));
    return `rgb(${r}, ${g}, ${b})`;
}

function getAvailabilityColor(freeCount, totalCount) {
    if (totalCount === 0) return "#3fb950";
    const fraction = Math.max(0, Math.min(1, freeCount / totalCount));
    
    // Gradient points: 0.0 -> #e04b4b, 0.25 -> #f2a93c, 0.5 -> #f5d76e, 0.75 -> #8fd35c, 1.0 -> #3fb950
    const stops = [
        { pos: 0.0, color: "#e04b4b" },
        { pos: 0.25, color: "#f2a93c" },
        { pos: 0.50, color: "#f5d76e" },
        { pos: 0.75, color: "#8fd35c" },
        { pos: 1.0, color: "#3fb950" }
    ];

    for (let i = 0; i < stops.length - 1; i++) {
        if (fraction >= stops[i].pos && fraction <= stops[i + 1].pos) {
            const range = stops[i + 1].pos - stops[i].pos;
            const factor = (fraction - stops[i].pos) / range;
            return interpolateColors(stops[i].color, stops[i + 1].color, factor);
        }
    }
    return "#3fb950";
}

async function loadHeatmapControls() {
    try {
        const [groupsData, friendsData] = await Promise.all([
            apiRequest("/groups"),
            apiRequest("/friends")
        ]);

        myGroupsList = groupsData.groups || [];
        myFriendsList = friendsData.friends || [];

        // Group Dropdown
        const groupSelect = document.getElementById("heatmap-group-select");
        groupSelect.innerHTML = '<option value="">Select Group</option>';
        myGroupsList.forEach(g => {
            const opt = document.createElement("option");
            opt.value = g.id;
            opt.textContent = `${g.name} (${g.member_count})`;
            groupSelect.appendChild(opt);
        });

        // Friends Checkboxes
        const friendsContainer = document.getElementById("heatmap-friends-checklist");
        friendsContainer.innerHTML = "";
        
        if (myFriendsList.length === 0) {
            friendsContainer.innerHTML = '<span class="text-xs text-slate-500 italic">No friends connected yet.</span>';
        } else {
            myFriendsList.forEach(f => {
                const item = document.createElement("label");
                item.className = "inline-flex items-center space-x-1.5 text-xs bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-md cursor-pointer hover:bg-slate-700 transition-all text-slate-200";
                item.innerHTML = `
                    <input type="checkbox" class="friend-compare-checkbox rounded bg-slate-900 border-slate-600 text-blue-600 focus:ring-blue-500" value="${f.id}" onchange="onFriendCheckboxChange()">
                    <span>${f.full_name}</span>
                `;
                friendsContainer.appendChild(item);
            });
        }

        // Auto-select first group if available
        if (myGroupsList.length > 0) {
            groupSelect.value = myGroupsList[0].id;
            loadGroupHeatmap(myGroupsList[0].id);
        } else {
            loadCustomHeatmap([currentUser.id]);
        }
    } catch (err) {
        showToast("Failed to load options: " + err.message, "error");
    }
}

async function onGroupSelectChange() {
    const groupId = document.getElementById("heatmap-group-select").value;
    if (groupId) {
        document.querySelectorAll(".friend-compare-checkbox").forEach(cb => cb.checked = false);
        loadGroupHeatmap(groupId);
    }
}

async function onFriendCheckboxChange() {
    const checked = Array.from(document.querySelectorAll(".friend-compare-checkbox:checked")).map(cb => parseInt(cb.value));
    if (checked.length > 0) {
        document.getElementById("heatmap-group-select").value = "";
        const allIds = [currentUser.id, ...checked];
        loadCustomHeatmap(allIds);
    } else {
        loadCustomHeatmap([currentUser.id]);
    }
}

function selectAllFriends() {
    document.querySelectorAll(".friend-compare-checkbox").forEach(cb => cb.checked = true);
    onFriendCheckboxChange();
}

function clearAllFriends() {
    document.querySelectorAll(".friend-compare-checkbox").forEach(cb => cb.checked = false);
    onFriendCheckboxChange();
}

async function loadGroupHeatmap(groupId) {
    try {
        const heatmap = await apiRequest(`/groups/${groupId}/heatmap`);
        renderHeatmap(heatmap);
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function loadCustomHeatmap(userIds) {
    try {
        const heatmap = await apiRequest(`/compare?user_ids=${userIds.join(",")}`);
        renderHeatmap(heatmap);
    } catch (err) {
        showToast(err.message, "error");
    }
}

function renderHeatmap(data) {
    currentHeatmapData = data;
    const gridContainer = document.getElementById("heatmap-matrix-grid");
    gridContainer.innerHTML = "";

    // Schedule Count Stat
    document.getElementById("stat-total-people").textContent = data.total_users;
    document.getElementById("stat-free-slots").textContent = data.best_slots.length;
    
    // Participants Chips
    const participantsContainer = document.getElementById("heatmap-participants-list");
    participantsContainer.innerHTML = "";
    data.users.forEach(u => {
        const chip = document.createElement("div");
        chip.className = "flex items-center space-x-1 px-2.5 py-0.5 bg-slate-800 border border-slate-700 rounded-md text-xs font-medium text-slate-300";
        chip.innerHTML = `
            <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${u.avatar_color || '#2563eb'}"></span>
            <span>${u.full_name}</span>
        `;
        participantsContainer.appendChild(chip);
    });

    // Best Slots Recommendations
    const bestSlotsBanner = document.getElementById("heatmap-best-slots-banner");
    const bestSlotsList = document.getElementById("heatmap-best-slots-list");
    bestSlotsList.innerHTML = "";
    
    if (data.best_slots.length > 0) {
        bestSlotsBanner.classList.remove("hidden");
        data.best_slots.slice(0, 8).forEach(slot => {
            const badge = document.createElement("span");
            badge.className = "inline-flex items-center px-2 py-0.5 bg-emerald-950/80 border border-emerald-700 text-emerald-300 rounded text-xs font-semibold mr-2 mb-1";
            badge.textContent = `${slot.day} ${slot.time_range}`;
            bestSlotsList.appendChild(badge);
        });
    } else {
        bestSlotsBanner.classList.add("hidden");
    }

    // Build Table (Exact visual replica of main.py matplotlib heatmap)
    const table = document.createElement("table");
    table.className = "w-full border-collapse text-center table-fixed text-xs";

    // Header Row (Times across top)
    const thead = document.createElement("thead");
    let headerHtml = `<tr class="bg-slate-900 text-slate-300 font-bold border-b border-slate-800">
        <th class="py-2.5 px-2 w-20 text-left uppercase tracking-wider text-[11px] font-extrabold text-slate-400">Day</th>`;
    data.time_slots.forEach((tLabel, tIdx) => {
        headerHtml += `<th class="py-2.5 px-1 font-bold text-slate-300 border-l border-slate-800">
            <div>${tLabel}</div>
            <div class="text-[10px] font-normal text-slate-500">${data.time_ranges[tIdx].split(' - ')[0]}</div>
        </th>`;
    });
    headerHtml += `</tr>`;
    thead.innerHTML = headerHtml;
    table.appendChild(thead);

    // Body (Days Mon-Fri)
    const tbody = document.createElement("tbody");
    data.grid.forEach((dayRow, dayIdx) => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-800/80";
        
        let rowHtml = `<td class="py-2.5 px-2 font-bold text-slate-300 bg-slate-900/90 text-left border-r border-slate-800 text-xs">
            ${data.days[dayIdx]}
        </td>`;

        dayRow.forEach((cell, timeIdx) => {
            if (cell.is_lunch) {
                rowHtml += `<td class="py-2 px-1 cell-lunch border-r border-slate-800">
                    <div class="text-xs font-bold text-slate-400">Lunch</div>
                </td>`;
            } else {
                const total = cell.total_users;
                const free = cell.free_count;
                const busy = cell.busy_users;
                const bgFraction = total > 0 ? (free / total) : 0;
                const bgColor = getAvailabilityColor(free, total);

                // Exact text color rule from main.py:
                // text_color = "white" if bg_frac < 0.3 or bg_frac > 0.9 else "#222222"
                const textColor = (bgFraction < 0.3 || bgFraction > 0.85) ? "#ffffff" : "#111827";

                // Exact sub_text rule from main.py:
                let subText = "all free";
                if (!busy || busy.length === 0) {
                    subText = "all free";
                } else if (busy.length === total) {
                    subText = "all busy";
                } else {
                    subText = busy.map(u => u.full_name).join(", ");
                }

                rowHtml += `<td class="py-2 px-1 heatmap-cell border-r border-slate-800" 
                    style="background-color: ${bgColor}; color: ${textColor};"
                    onclick="openSlotDetailModal(${dayIdx}, ${timeIdx})"
                    title="${cell.day_name} ${cell.time_range}: ${cell.free_count}/${cell.total_users} free">
                    <div class="font-extrabold text-sm leading-tight">${free}/${total}</div>
                    <div class="text-[10px] font-medium truncate px-1 opacity-95">${subText}</div>
                </td>`;
            }
        });

        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    gridContainer.appendChild(table);
}

// Slot Breakdown Modal
function openSlotDetailModal(dayIdx, timeIdx) {
    if (!currentHeatmapData) return;
    const cell = currentHeatmapData.grid[dayIdx][timeIdx];
    if (cell.is_lunch) return;

    const modal = document.getElementById("slot-detail-modal");
    document.getElementById("modal-slot-title").textContent = `${cell.day_name} at ${cell.time_range}`;
    document.getElementById("modal-slot-ratio").textContent = `${cell.free_count} of ${cell.total_users} Free (${cell.free_percentage}%)`;

    // Free List
    const freeList = document.getElementById("modal-free-list");
    freeList.innerHTML = "";
    if (cell.free_users.length === 0) {
        freeList.innerHTML = '<li class="text-xs text-slate-500 italic">None</li>';
    } else {
        cell.free_users.forEach(u => {
            const li = document.createElement("li");
            li.className = "flex items-center space-x-2 text-xs font-medium text-emerald-400 bg-emerald-950/40 px-2.5 py-1.5 rounded border border-emerald-900";
            li.innerHTML = `
                <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${u.avatar_color || '#10b981'}"></span>
                <span>${u.full_name} (${u.reg_no || `@${u.username}`})</span>
            `;
            freeList.appendChild(li);
        });
    }

    // Busy List
    const busyList = document.getElementById("modal-busy-list");
    busyList.innerHTML = "";
    if (cell.busy_users.length === 0) {
        busyList.innerHTML = '<li class="text-xs text-emerald-400 italic">All members are free during this slot.</li>';
    } else {
        cell.busy_users.forEach(u => {
            const li = document.createElement("li");
            li.className = "flex items-center space-x-2 text-xs font-medium text-rose-300 bg-rose-950/40 px-2.5 py-1.5 rounded border border-rose-900";
            li.innerHTML = `
                <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${u.avatar_color || '#ef4444'}"></span>
                <span>${u.full_name} - Has Class</span>
            `;
            busyList.appendChild(li);
        });
    }

    modal.classList.remove("hidden");
}

function closeSlotDetailModal() {
    document.getElementById("slot-detail-modal").classList.add("hidden");
}

async function handleCreateShareLink() {
    const groupId = document.getElementById("heatmap-group-select").value;
    try {
        const payload = {
            title: groupId ? `Group Schedule Heatmap` : `${currentUser.full_name} Availability`,
            group_id: groupId ? parseInt(groupId) : null,
            user_id: groupId ? null : currentUser.id,
            expires_in_days: 30
        };

        const result = await apiRequest("/share/create", {
            method: "POST",
            body: JSON.stringify(payload)
        });

        const fullUrl = `${window.location.origin}${result.share_url}`;
        navigator.clipboard.writeText(fullUrl);
        showToast("Share link copied to clipboard.");
    } catch (err) {
        showToast("Error creating share link: " + err.message, "error");
    }
}

// ==============================================================================
// TAB 2: Timetable Editor & OCR
// ==============================================================================
async function loadMyTimetable() {
    try {
        const data = await apiRequest("/timetable/my-slots");
        currentTimetableData = data;
        renderTimetableEditor(data);
    } catch (err) {
        showToast("Error loading timetable: " + err.message, "error");
    }
}

function renderTimetableEditor(data) {
    const container = document.getElementById("timetable-editor-grid");
    container.innerHTML = "";

    const table = document.createElement("table");
    table.className = "w-full border-collapse text-center table-fixed text-xs";

    const thead = document.createElement("thead");
    let headerHtml = `<tr class="bg-slate-900 text-slate-300 font-bold border-b border-slate-800">
        <th class="py-2.5 px-2 w-20 text-left uppercase text-slate-400">Day</th>`;
    data.time_slots.forEach((tLabel, tIdx) => {
        headerHtml += `<th class="py-2.5 px-1 font-bold text-slate-300 border-l border-slate-800">
            <div>${tLabel}</div>
            <div class="text-[10px] font-normal text-slate-500">${data.time_ranges[tIdx].split(' - ')[0]}</div>
        </th>`;
    });
    headerHtml += `</tr>`;
    thead.innerHTML = headerHtml;
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    data.slot_details.forEach((dayRow, dayIdx) => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-800/80";

        let rowHtml = `<td class="py-2.5 px-2 font-bold text-slate-300 bg-slate-900/90 text-left border-r border-slate-800 uppercase">
            ${data.days[dayIdx]}
        </td>`;

        dayRow.forEach((slot, timeIdx) => {
            if (timeIdx === 6) {
                rowHtml += `<td class="py-2.5 px-1 bg-slate-900 border-r border-slate-800 text-slate-600 font-medium">Lunch</td>`;
            } else {
                const isBusy = slot.is_busy === 1;
                const slotClass = isBusy ? "is-busy" : "is-free";
                const slotText = isBusy ? "BUSY" : "FREE";
                const codeBadge = slot.slot_code ? `<div class="text-[10px] font-mono text-slate-400 mt-0.5">${slot.slot_code}</div>` : "";

                rowHtml += `<td id="slot-cell-${dayIdx}-${timeIdx}" 
                    class="py-2 px-1 slot-editable ${slotClass} border-r border-slate-800 cursor-pointer"
                    onclick="toggleSlotState(${dayIdx}, ${timeIdx})">
                    <div class="font-extrabold text-xs">${slotText}</div>
                    ${codeBadge}
                </td>`;
            }
        });

        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.appendChild(table);
}

function toggleSlotState(dayIdx, timeIdx) {
    if (!currentTimetableData) return;
    const slot = currentTimetableData.slot_details[dayIdx][timeIdx];
    slot.is_busy = (slot.is_busy === 1) ? 0 : 1;
    currentTimetableData.matrix[dayIdx][timeIdx] = slot.is_busy;

    const cellEl = document.getElementById(`slot-cell-${dayIdx}-${timeIdx}`);
    if (cellEl) {
        if (slot.is_busy === 1) {
            cellEl.className = "py-2 px-1 slot-editable is-busy border-r border-slate-800 cursor-pointer";
            cellEl.querySelector("div").textContent = "BUSY";
        } else {
            cellEl.className = "py-2 px-1 slot-editable is-free border-r border-slate-800 cursor-pointer";
            cellEl.querySelector("div").textContent = "FREE";
        }
    }
}

function setAllTimetableSlots(busyState) {
    if (!currentTimetableData) return;
    for (let d = 0; d < 5; d++) {
        for (let t = 0; t < 11; t++) {
            if (t !== 6) { // Skip lunch break
                const isBusyVal = busyState ? 1 : 0;
                currentTimetableData.slot_details[d][t].is_busy = isBusyVal;
                currentTimetableData.matrix[d][t] = isBusyVal;
            }
        }
    }
    renderTimetableEditor(currentTimetableData);
    showToast(busyState ? "All slots marked busy (click Save to persist)." : "All slots marked free (click Save to persist).", "info");
}

async function saveTimetableSlots() {
    if (!currentTimetableData) return;
    try {
        const slotsPayload = [];
        for (let d = 0; d < 5; d++) {
            for (let t = 0; t < 11; t++) {
                const s = currentTimetableData.slot_details[d][t];
                slotsPayload.push({
                    day_of_week: d,
                    time_index: t,
                    is_busy: s.is_busy,
                    slot_code: s.slot_code,
                    course_name: s.course_name
                });
            }
        }

        await apiRequest("/timetable/update-slots", {
            method: "POST",
            body: JSON.stringify({ slots: slotsPayload })
        });
        showToast("Schedule updated successfully.");
    } catch (err) {
        showToast("Failed to save schedule: " + err.message, "error");
    }
}

async function clearAllTimetableSlots() {
    try {
        await apiRequest("/timetable/clear-slots", { method: "POST" });
        showToast("All slots reset to free.");
        loadMyTimetable();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleOcrUpload(fileInput) {
    if (!fileInput.files || fileInput.files.length === 0) return;
    const file = fileInput.files[0];

    const formData = new FormData();
    formData.append("file", file);

    const statusBanner = document.getElementById("ocr-status-indicator");
    statusBanner.classList.remove("hidden");
    statusBanner.innerHTML = `
        <div class="flex items-center space-x-2 text-blue-400 text-xs font-medium">
            <span class="animate-spin inline-block w-3.5 h-3.5 border-2 border-blue-400 border-t-transparent rounded-full"></span>
            <span>Scanning timetable with cell-by-cell OCR...</span>
        </div>
    `;

    try {
        const res = await apiRequest("/timetable/upload-ocr", {
            method: "POST",
            body: formData
        });

        if (res.ocr_result && res.ocr_result.success) {
            showToast(`OCR completed: Detected ${res.ocr_result.busy_count} busy slot(s).`);
            loadMyTimetable();
        } else {
            showToast(res.ocr_result?.error || "OCR completed. Please review.", "warning");
            loadMyTimetable();
        }
    } catch (err) {
        showToast("OCR processing error: " + err.message, "error");
    } finally {
        statusBanner.classList.add("hidden");
        fileInput.value = "";
    }
}

// ==============================================================================
// TAB 3: Friends Hub
// ==============================================================================
async function loadFriendsHub() {
    try {
        const data = await apiRequest("/friends");
        
        // Incoming
        const incomingContainer = document.getElementById("incoming-requests-list");
        incomingContainer.innerHTML = "";
        if (data.incoming_requests.length === 0) {
            incomingContainer.innerHTML = '<p class="text-xs text-slate-500 italic">No pending requests.</p>';
        } else {
            data.incoming_requests.forEach(req => {
                const card = document.createElement("div");
                card.className = "flex items-center justify-between p-2.5 bg-slate-900 border border-slate-800 rounded-lg";
                card.innerHTML = `
                    <div class="flex items-center space-x-2.5">
                        <div class="w-7 h-7 rounded-full flex items-center justify-center font-bold text-white text-xs" style="background-color: ${req.avatar_color || '#2563eb'}">
                            ${req.full_name.charAt(0)}
                        </div>
                        <div>
                            <div class="text-xs font-bold text-slate-200">${req.full_name}</div>
                            <div class="text-[10px] text-slate-500">${req.reg_no || `@${req.username}`}</div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-1.5">
                        <button onclick="respondFriendRequest(${req.request_id}, 'accepted')" class="px-2 py-1 bg-emerald-600 text-white rounded text-xs font-semibold hover:bg-emerald-700">Accept</button>
                        <button onclick="respondFriendRequest(${req.request_id}, 'rejected')" class="px-2 py-1 bg-slate-800 text-slate-300 rounded text-xs font-semibold hover:bg-slate-700">Decline</button>
                    </div>
                `;
                incomingContainer.appendChild(card);
            });
        }

        // Friends List
        const friendsContainer = document.getElementById("accepted-friends-list");
        friendsContainer.innerHTML = "";
        if (data.friends.length === 0) {
            friendsContainer.innerHTML = '<p class="text-xs text-slate-500 italic">No friends connected yet. Search above to add peers.</p>';
        } else {
            data.friends.forEach(f => {
                const card = document.createElement("div");
                card.className = "flex items-center justify-between p-2.5 bg-slate-900 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors";
                card.innerHTML = `
                    <div class="flex items-center space-x-2.5">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-white text-xs" style="background-color: ${f.avatar_color || '#2563eb'}">
                            ${f.full_name.charAt(0)}
                        </div>
                        <div>
                            <div class="text-xs font-bold text-slate-200">${f.full_name}</div>
                            <div class="text-[10px] text-slate-500">${f.reg_no || `@${f.username}`} &bull; ${f.campus}</div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button onclick="quickCompareWithFriend(${f.id})" class="px-2.5 py-1 bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 rounded text-xs font-semibold transition-colors">
                            Compare
                        </button>
                        <button onclick="removeFriend(${f.id})" class="p-1 text-slate-500 hover:text-rose-400 transition-colors" title="Remove">
                            &times;
                        </button>
                    </div>
                `;
                friendsContainer.appendChild(card);
            });
        }
    } catch (err) {
        showToast("Error loading friends: " + err.message, "error");
    }
}

let searchDebounceTimer = null;
function onFriendSearchInput(query) {
    clearTimeout(searchDebounceTimer);
    if (!query || query.trim().length < 2) {
        document.getElementById("search-results-list").innerHTML = "";
        return;
    }

    searchDebounceTimer = setTimeout(async () => {
        try {
            const data = await apiRequest(`/friends/search?q=${encodeURIComponent(query.trim())}`);
            renderSearchResults(data.results);
        } catch (err) {
            console.error("Search error:", err);
        }
    }, 250);
}

function renderSearchResults(results) {
    const container = document.getElementById("search-results-list");
    container.innerHTML = "";

    if (results.length === 0) {
        container.innerHTML = '<p class="text-xs text-slate-500 italic p-1">No matching students found.</p>';
        return;
    }

    results.forEach(res => {
        const item = document.createElement("div");
        item.className = "flex items-center justify-between p-2 bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-850";

        let actionBtn = "";
        if (res.friendship_status === "friend") {
            actionBtn = `<span class="px-2 py-0.5 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded text-[10px] font-bold">Connected</span>`;
        } else if (res.friendship_status === "request_sent") {
            actionBtn = `<span class="px-2 py-0.5 bg-amber-950 text-amber-400 border border-amber-800 rounded text-[10px] font-bold">Pending</span>`;
        } else if (res.friendship_status === "request_received") {
            actionBtn = `<button onclick="respondFriendRequest(${res.friendship_id}, 'accepted')" class="px-2 py-1 bg-emerald-600 text-white rounded text-xs font-semibold">Accept</button>`;
        } else {
            actionBtn = `<button onclick="sendFriendRequest(${res.id})" class="px-2 py-1 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700">+ Add</button>`;
        }

        item.innerHTML = `
            <div class="flex items-center space-x-2">
                <div class="w-6 h-6 rounded-full flex items-center justify-center font-bold text-white text-[10px]" style="background-color: ${res.avatar_color || '#2563eb'}">
                    ${res.full_name.charAt(0)}
                </div>
                <div>
                    <div class="text-xs font-bold text-slate-200">${res.full_name}</div>
                    <div class="text-[10px] text-slate-500">${res.reg_no || `@${res.username}`}</div>
                </div>
            </div>
            <div>${actionBtn}</div>
        `;
        container.appendChild(item);
    });
}

async function sendFriendRequest(userId) {
    try {
        const res = await apiRequest("/friends/request", {
            method: "POST",
            body: JSON.stringify({ target_user_id: userId })
        });
        showToast(res.message);
        loadFriendsHub();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function respondFriendRequest(friendshipId, action) {
    try {
        const res = await apiRequest("/friends/respond", {
            method: "POST",
            body: JSON.stringify({ friendship_id: friendshipId, action: action })
        });
        showToast(res.message);
        loadFriendsHub();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function removeFriend(friendId) {
    if (!confirm("Remove this connection?")) return;
    try {
        await apiRequest(`/friends/${friendId}`, { method: "DELETE" });
        showToast("Connection removed.");
        loadFriendsHub();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function quickCompareWithFriend(friendId) {
    switchTab("heatmap");
    setTimeout(() => {
        loadCustomHeatmap([currentUser.id, friendId]);
    }, 80);
}

// ==============================================================================
// TAB 4: Groups Hub
// ==============================================================================
async function loadGroupsHub() {
    try {
        const data = await apiRequest("/groups");
        const container = document.getElementById("groups-card-list");
        container.innerHTML = "";

        if (data.groups.length === 0) {
            container.innerHTML = '<p class="text-xs text-slate-500 italic">No groups yet. Create one or join with an invite code.</p>';
            return;
        }

        data.groups.forEach(g => {
            const card = document.createElement("div");
            card.className = "bg-slate-900 p-4 rounded-xl border border-slate-800 flex flex-col justify-between";
            card.innerHTML = `
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="font-bold text-slate-200 text-sm">${g.name}</h4>
                        <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${g.my_role === 'admin' ? 'bg-blue-950 text-blue-400 border border-blue-800' : 'bg-slate-800 text-slate-400'}">
                            ${g.my_role}
                        </span>
                    </div>
                    <p class="text-xs text-slate-400 mb-3">${g.description || 'No description.'}</p>
                    
                    <div class="flex items-center justify-between text-xs bg-slate-950 p-2 rounded border border-slate-800 mb-3">
                        <span class="text-slate-400">Invite Code: <strong class="font-mono text-blue-400">${g.invite_code}</strong></span>
                        <button onclick="navigator.clipboard.writeText('${g.invite_code}'); showToast('Code copied.');" class="text-blue-400 hover:text-blue-300 font-bold text-xs">Copy</button>
                    </div>
                </div>

                <div class="flex items-center justify-between pt-2.5 border-t border-slate-800">
                    <span class="text-xs text-slate-400">${g.member_count} member(s)</span>
                    <button onclick="viewGroupHeatmapDirect(${g.id})" class="px-3 py-1 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700 transition-colors">
                        View Heatmap &rarr;
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        showToast("Error loading groups: " + err.message, "error");
    }
}

async function handleCreateGroup(name, description) {
    if (!name || name.trim().length < 2) {
        showToast("Please enter group name.", "error");
        return;
    }
    try {
        const res = await apiRequest("/groups/create", {
            method: "POST",
            body: JSON.stringify({ name: name.trim(), description: description ? description.trim() : null })
        });
        showToast(res.message);
        document.getElementById("create-group-modal").classList.add("hidden");
        loadGroupsHub();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleJoinGroup(inviteCode) {
    if (!inviteCode || inviteCode.trim().length < 4) {
        showToast("Enter invite code.", "error");
        return;
    }
    try {
        const res = await apiRequest("/groups/join", {
            method: "POST",
            body: JSON.stringify({ invite_code: inviteCode.trim().toUpperCase() })
        });
        showToast(res.message);
        document.getElementById("join-group-input").value = "";
        loadGroupsHub();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function viewGroupHeatmapDirect(groupId) {
    switchTab("heatmap");
    setTimeout(() => {
        document.getElementById("heatmap-group-select").value = groupId;
        loadGroupHeatmap(groupId);
    }, 80);
}

window.addEventListener("DOMContentLoaded", initApp);
