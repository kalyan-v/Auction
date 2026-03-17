/**
 * WPL Auction System - Auction Page
 *
 * Handles all auction room functionality:
 * - Real-time bidding with team selection
 * - Player randomizer with slot machine animation
 * - Auction state management (start, end, sold, unsold)
 * - Price reset and bid history tracking
 * - Timer countdown for auction duration
 * - Confetti celebration on successful sales
 * - Unsold mode toggle for re-auctioning players
 *
 * Bid increment: Tiered (configured per league, default 25 Lakhs per click)
 * Base currency unit: Lakhs (1 Lakh = 100,000 INR)
 */
let currentPlayerId = null;
let timerInterval = null;
let selectedTeamId = null;
let selectedTeamName = null;
let currentBidPrice = 0;
let leadingTeamName = '-';
let unsoldModeEnabled = false;
let autoStartTimer = null;

function cancelAutoStart() {
    if (autoStartTimer) {
        clearTimeout(autoStartTimer);
        autoStartTimer = null;
        const hint = document.querySelector('.auto-start-hint');
        if (hint) hint.textContent = '❌ Auto-start cancelled';
        showNotification('Auto-start cancelled', 'info');
    }
}

// Toggle Unsold Mode
function toggleUnsoldMode() {
    const unsoldCheckbox = document.getElementById('unsoldMode');
    if (!unsoldCheckbox) return;

    unsoldModeEnabled = unsoldCheckbox.checked;
    const modeLabel = document.getElementById('modeLabel');
    const randomizerSection = document.querySelector('.randomizer-section');

    if (unsoldModeEnabled) {
        if (modeLabel) modeLabel.textContent = '🔄 UNSOLD Mode (Unsold players included)';
        if (randomizerSection) randomizerSection.classList.add('unsold-mode');
        showNotification('Unsold Mode ON - Unsold players are now in the pool', 'info');
    } else {
        if (modeLabel) modeLabel.textContent = 'Normal Mode';
        if (randomizerSection) randomizerSection.classList.remove('unsold-mode');
        showNotification('Normal Mode - Only new players in pool', 'info');
    }
}

// Initialize auctioneer panel
function initAuctioneerPanel() {
    // Get current player ID from the page if auction is active
    const playerCard = document.getElementById('currentPlayer');
    if (playerCard && playerCard.dataset.playerId) {
        currentPlayerId = parseInt(playerCard.dataset.playerId, 10);
    }

    // Get initial price from page if auction is active
    const priceEl = document.getElementById('currentPrice');
    if (priceEl && priceEl.textContent) {
        currentBidPrice = parseFloat(priceEl.textContent) || 50;
    }

    // Get initial leading team from server data (fixes bug where page reload loses leading team)
    const leadingTeamEl = document.getElementById('leadingTeam');
    if (leadingTeamEl && leadingTeamEl.dataset.initialTeam) {
        leadingTeamName = leadingTeamEl.dataset.initialTeam;
    }

    updateBidDisplay();
}

// Bid increment tiers - uses league config if available, falls back to flat 25L
const _bidTiers = (typeof BID_INCREMENT_TIERS !== 'undefined' && Array.isArray(BID_INCREMENT_TIERS))
    ? BID_INCREMENT_TIERS.sort((a, b) => a.threshold - b.threshold)
    : [{ threshold: 0, increment: 2500000 }];

/**
 * Get the bid increment for a given price (in Lakhs).
 * Prices internally are in Lakhs; tiers store raw values.
 * Returns increment in Lakhs.
 */
function getBidIncrement(currentPriceLakhs) {
    const currentRaw = currentPriceLakhs * 100000;
    let applicable = _bidTiers[0];
    for (const tier of _bidTiers) {
        if (currentRaw >= tier.threshold) {
            applicable = tier;
        }
    }
    return applicable.increment / 100000; // convert to Lakhs
}

// Helper to select team from data attributes (safe for special characters)
function selectTeamFromData(btn) {
    const teamId = parseInt(btn.dataset.teamId, 10);
    const teamName = btn.dataset.teamName;
    selectTeam(teamId, teamName);
}

// Prevent double-clicks
let isProcessingBid = false;

// Select team for bidding - first click = base price, subsequent clicks add tiered increment
async function selectTeam(teamId, teamName) {
    if (isProcessingBid) return;

    if (!currentPlayerId) {
        showNotification('No active auction!', 'error');
        return;
    }

    isProcessingBid = true;

    // Calculate bid amount:
    // - If no bids yet (leadingTeamName is '-'), bid at base price
    // - Otherwise, add tiered increment
    let newBidPrice;
    let isBasePriceBid = false;
    const increment = getBidIncrement(currentBidPrice);
    
    if (leadingTeamName === '-') {
        // First bid - use base price
        newBidPrice = currentBidPrice;
        isBasePriceBid = true;
    } else {
        // Subsequent bid - add tiered increment
        newBidPrice = currentBidPrice + increment;
    }
    
    const bidAmount = newBidPrice * 100000;
    
    try {
        const response = await secureFetch('/api/bid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_id: currentPlayerId,
                team_id: teamId,
                amount: bidAmount
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update state AFTER successful API call (prevents race condition)
            selectedTeamId = teamId;
            selectedTeamName = teamName;
            currentBidPrice = newBidPrice;
            leadingTeamName = teamName;

            // Update UI only after success
            document.querySelectorAll('.team-btn').forEach(btn => btn.classList.remove('selected'));
            const selectedBtn = document.querySelector(`.team-btn[data-team-id="${teamId}"]`);
            if (selectedBtn) {
                selectedBtn.classList.add('selected');
            }
            const selectedTeamEl = document.getElementById('selectedTeamName');
            if (selectedTeamEl) selectedTeamEl.textContent = teamName;

            updateBidDisplay();

            if (isBasePriceBid) {
                showNotification(`${teamName} bids ₹${newBidPrice} L (base price)`, 'success');
            } else {
                showNotification(`${teamName} bids ₹${newBidPrice} L (+${increment}L)`, 'success');
            }
            addToBidHistory(teamName, newBidPrice);
        } else {
            showNotification(data.error || 'Bid failed', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error placing bid', 'error');
    } finally {
        isProcessingBid = false;
    }
}

function updateBidDisplay() {
    const bigPrice = document.getElementById('bigCurrentPrice');
    const leadingTeam = document.getElementById('leadingTeam');
    const currentPriceEl = document.getElementById('currentPrice');
    
    // Format price display
    let priceText;
    if (currentBidPrice >= 100) {
        priceText = `₹${(currentBidPrice / 100).toFixed(2)} Cr`;
    } else {
        priceText = `₹${currentBidPrice} L`;
    }
    
    if (bigPrice) bigPrice.textContent = priceText;
    if (leadingTeam) leadingTeam.textContent = leadingTeamName;
    if (currentPriceEl) currentPriceEl.textContent = currentBidPrice;
}

function addToBidHistory(teamName, amount) {
    const bidList = document.getElementById('bidList');
    if (bidList) {
        const bidItem = document.createElement('div');
        bidItem.className = 'bid-history-item';
        bidItem.textContent = `${teamName}: ₹${amount} L`;
        bidList.insertBefore(bidItem, bidList.firstChild);
    }
}

function resetPrice() {
    const resetInput = document.getElementById('resetPriceInput');
    if (!resetInput) return;

    const newPrice = parseFloat(resetInput.value);

    if (isNaN(newPrice) || newPrice <= 0) {
        showNotification('Enter a valid price!', 'error');
        return;
    }

    if (!currentPlayerId) {
        showNotification('No active auction!', 'error');
        return;
    }

    if (!confirm(`Reset price to ₹${newPrice} L?`)) {
        return;
    }

    // Find and disable reset button
    const resetBtn = resetInput.nextElementSibling;
    if (resetBtn) {
        resetBtn.disabled = true;
        resetBtn.textContent = '⏳ Resetting...';
    }

    // Call API to persist price reset
    secureFetch('/api/auction/reset-price', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price: newPrice * 100000 })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentBidPrice = newPrice;
            leadingTeamName = '-';  // Reset leading team

            // Clear selected team state and animation
            selectedTeamId = null;
            selectedTeamName = null;
            document.querySelectorAll('.team-btn').forEach(btn => btn.classList.remove('selected'));
            const selectedTeamEl = document.getElementById('selectedTeamName');
            if (selectedTeamEl) selectedTeamEl.textContent = '-';

            updateBidDisplay();

            // Clear the input
            resetInput.value = '';

            showNotification(`Price reset to ₹${newPrice} L`, 'success');

            // Add to bid history
            const bidList = document.getElementById('bidList');
            if (bidList) {
                const bidItem = document.createElement('div');
                bidItem.className = 'bid-history-item price-reset';
                bidItem.textContent = `⚠️ Price reset to ₹${newPrice} L`;
                bidList.insertBefore(bidItem, bidList.firstChild);
            }
        } else {
            showNotification(data.error || 'Failed to reset price', 'error');
        }
    })
    .catch(error => {
        showNotification('Error resetting price', 'error');
    })
    .finally(() => {
        if (resetBtn) {
            resetBtn.disabled = false;
            resetBtn.textContent = 'Reset Price';
        }
    });
}

async function markSold() {
    if (!currentPlayerId || leadingTeamName === '-') {
        showNotification('No valid bid to finalize!', 'error');
        return;
    }

    const rtmCheckbox = document.getElementById('rtmCheckbox');
    const isRtm = rtmCheckbox ? rtmCheckbox.checked : false;
    const rtmLabel = isRtm ? ' (RTM)' : '';

    if (!confirm(`Confirm SOLD${rtmLabel} to ${leadingTeamName} for ₹${currentBidPrice >= 100 ? (currentBidPrice/100).toFixed(2) + ' Cr' : currentBidPrice + ' L'}?`)) {
        return;
    }

    const soldBtn = document.getElementById('soldBtn');
    if (soldBtn) {
        soldBtn.disabled = true;
        soldBtn.textContent = '⏳ Processing...';
    }

    try {
        const response = await secureFetch('/api/auction/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_rtm: isRtm })
        });
        const data = await response.json();

        if (data.success) {
            // Reset RTM checkbox for next auction
            if (rtmCheckbox) rtmCheckbox.checked = false;
            // Trigger confetti celebration!
            triggerConfetti();
            showNotification(`🎉 SOLD to ${leadingTeamName}!`, 'success');
            setTimeout(() => location.reload(), 2500);
        } else {
            showNotification(data.error || 'Error ending auction', 'error');
            if (soldBtn) {
                soldBtn.disabled = false;
                soldBtn.textContent = '✅ SOLD!';
            }
        }
    } catch (error) {
        showNotification('Error ending auction', 'error');
        if (soldBtn) {
            soldBtn.disabled = false;
            soldBtn.textContent = '✅ SOLD!';
        }
    }
}

// Confetti celebration function
function triggerConfetti() {
    // Check if confetti library is loaded
    if (typeof confetti === 'undefined') {
        console.log('Confetti library not loaded');
        return;
    }
    
    // Fire confetti from both sides
    const duration = 3000;
    const end = Date.now() + duration;
    
    // Team colors based confetti
    const colors = ['#667eea', '#764ba2', '#ffd700', '#00ff88', '#ff6b6b'];
    
    (function frame() {
        confetti({
            particleCount: 5,
            angle: 60,
            spread: 55,
            origin: { x: 0, y: 0.7 },
            colors: colors
        });
        confetti({
            particleCount: 5,
            angle: 120,
            spread: 55,
            origin: { x: 1, y: 0.7 },
            colors: colors
        });
        
        if (Date.now() < end) {
            requestAnimationFrame(frame);
        }
    }());
    
    // Also fire a big burst in the center
    confetti({
        particleCount: 100,
        spread: 100,
        origin: { x: 0.5, y: 0.5 },
        colors: colors
    });
}

async function markUnsold() {
    if (!confirm('Mark this player as UNSOLD?')) {
        return;
    }

    const unsoldBtn = document.getElementById('unsoldBtn');
    if (unsoldBtn) {
        unsoldBtn.disabled = true;
        unsoldBtn.textContent = '⏳ Processing...';
    }

    try {
        const response = await secureFetch('/api/auction/unsold', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showNotification('Player marked as UNSOLD', 'info');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification(data.error || 'Error', 'error');
            if (unsoldBtn) {
                unsoldBtn.disabled = false;
                unsoldBtn.textContent = '❌ UNSOLD';
            }
        }
    } catch (error) {
        showNotification('Error marking unsold', 'error');
        if (unsoldBtn) {
            unsoldBtn.disabled = false;
            unsoldBtn.textContent = '❌ UNSOLD';
        }
    }
}

// Persist category filter selection across page reloads
function initCategoryFilter() {
    const categoryEl = document.getElementById('categoryFilter');
    if (!categoryEl) return;

    // Restore saved selection
    const saved = sessionStorage.getItem('auctionCategoryFilter');
    if (saved !== null) {
        // Only restore if the option still exists in the dropdown
        const optionExists = Array.from(categoryEl.options).some(o => o.value === saved);
        if (optionExists) {
            categoryEl.value = saved;
        }
    }

    // Save on change
    categoryEl.addEventListener('change', () => {
        sessionStorage.setItem('auctionCategoryFilter', categoryEl.value);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initAuctioneerPanel();
    initCategoryFilter();
});

// Pick random player from selected position with animation
async function pickRandomPlayer() {
    const categoryEl = document.getElementById('categoryFilter');
    const category = categoryEl ? categoryEl.value : '';
    const resultDiv = document.getElementById('randomResult');
    const btn = document.getElementById('pickRandomBtn');
    
    // Disable button during animation
    btn.disabled = true;
    btn.innerHTML = '🎰 Selecting...';
    
    try {
        // Build URL with category filter and unsold mode
        let url = '/api/players/available';
        const params = [];
        if (category) params.push(`auction_category=${encodeURIComponent(category)}`);
        if (unsoldModeEnabled) params.push('include_unsold=true');
        if (params.length > 0) url += '?' + params.join('&');
        const response = await secureFetch(url);
        const data = await response.json();

        if (!data.success || data.players.length === 0) {
            resultDiv.innerHTML = `<p style="color: #e74c3c;">${escapeHtml(data.error || 'No available players')}</p>`;
            resultDiv.classList.add('show');
            btn.disabled = false;
            btn.innerHTML = '🎲 Pick Random Player';
            return;
        }
        
        const players = data.players;
        resultDiv.classList.add('show');
        resultDiv.classList.add('spinning');
        
        // Slot machine animation - cycle through names
        let cycles = 0;
        const totalCycles = 14;
        let delay = 40;
        
        const animate = () => {
            const randomIndex = Math.floor(Math.random() * players.length);
            const player = players[randomIndex];
            
            resultDiv.innerHTML = `
                <div class="spinning-name">
                    <h3>${escapeHtml(player.name)}</h3>
                    <p>${escapeHtml(player.position)}</p>
                </div>
            `;
            
            cycles++;
            
            if (cycles < totalCycles) {
                // Slow down gradually
                delay = 50 + (cycles * 15);
                setTimeout(animate, delay);
            } else {
                // Final selection - get actual random from server
                selectFinalPlayer(category, resultDiv, btn);
            }
        };
        
        animate();
        
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error picking random player', 'error');
        btn.disabled = false;
        btn.innerHTML = '🎲 Pick Random Player';
    }
}

async function selectFinalPlayer(category, resultDiv, btn) {
    try {
        // Build URL with category and unsold mode
        let url = '/api/players/random';
        const params = [];
        if (category) params.push(`auction_category=${encodeURIComponent(category)}`);
        if (unsoldModeEnabled) params.push('include_unsold=true');
        if (params.length > 0) url += '?' + params.join('&');

        const response = await secureFetch(url);
        const data = await response.json();

        resultDiv.classList.remove('spinning');

        if (data.success) {
            const player = data.player;
            resultDiv.innerHTML = `
                <div class="final-result">
                    <div class="confetti">🎉</div>
                    <h3>${escapeHtml(player.name)}</h3>
                    <p>${escapeHtml(player.position)} | Base Price: ₹${player.base_price / 100000} L</p>
                    <p class="auto-start-hint">⏳ Starting auction in 2 seconds...</p>
                    <button class="btn btn-small btn-danger" onclick="cancelAutoStart()">✋ Cancel</button>
                </div>
            `;
            // Auto-start auction after 2 seconds and scroll to top
            autoStartTimer = setTimeout(() => {
                autoStartTimer = null;
                startAuction(parseInt(player.id, 10));
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }, 2000);
        } else {
            resultDiv.innerHTML = `<p style="color: #e74c3c;">${escapeHtml(data.error)}</p>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.classList.remove('spinning');
        resultDiv.innerHTML = `<p style="color: #e74c3c;">Error selecting player</p>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🎲 Pick Random Player';
    }
}

// Start auction for a player
let isStartingAuction = false;
async function startAuction(playerId) {
    if (isStartingAuction) return;
    isStartingAuction = true;

    // Find and disable the clicked button
    const btn = document.querySelector(`[onclick="startAuction(${playerId})"]`);
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Starting...';
    }

    try {
        const response = await secureFetch(`/api/auction/start/${playerId}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Auction started!', 'success');
            currentPlayerId = playerId;
            location.reload(); // Reload to show updated state
        } else {
            showNotification(data.error || 'Failed to start auction', 'error');
            if (btn) {
                btn.disabled = false;
                btn.textContent = btn.classList.contains('btn-retry') ? '🔄 Retry' : 'Start Auction';
            }
            isStartingAuction = false;
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error starting auction', 'error');
        if (btn) {
            btn.disabled = false;
            btn.textContent = btn.classList.contains('btn-retry') ? '🔄 Retry' : 'Start Auction';
        }
        isStartingAuction = false;
    }
}

// End auction
document.getElementById('endAuctionBtn')?.addEventListener('click', async function() {
    if (!confirm('Are you sure you want to end the current auction?')) {
        return;
    }

    const rtmCheckbox = document.getElementById('rtmCheckbox');
    const isRtm = rtmCheckbox ? rtmCheckbox.checked : false;

    const btn = this;
    btn.disabled = true;
    btn.textContent = '⏳ Ending...';

    try {
        const response = await secureFetch('/api/auction/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_rtm: isRtm })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Auction ended!', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification(data.error || 'Failed to end auction', 'error');
            btn.disabled = false;
            btn.textContent = 'End Current Auction';
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error ending auction', 'error');
        btn.disabled = false;
        btn.textContent = 'End Current Auction';
    }
});

// Timer countdown (simple client-side version)
function initTimer() {
    const timerEl = document.getElementById('timer');
    if (!timerEl) return;

    let timeRemaining = parseInt(timerEl.textContent, 10) || 0;
    if (timeRemaining <= 0) return;

    // Clear any existing interval
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    timerInterval = setInterval(() => {
        timeRemaining--;
        const el = document.getElementById('timer');

        if (!el) {
            // Timer element was removed from DOM, clean up interval
            clearInterval(timerInterval);
            timerInterval = null;
            return;
        }

        el.textContent = timeRemaining;

        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            timerInterval = null;
            showNotification('Time is up!', 'info');
        }
    }, 1000);
}

// Initialize timer on page load
initTimer();

// Clean up timer on page unload to prevent memory leaks
window.addEventListener('beforeunload', () => {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
});
