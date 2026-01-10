// Auction page functionality
let currentPlayerId = null;
let timerInterval = null;
let selectedTeamId = null;
let selectedTeamName = null;
let currentBidPrice = 0;
let leadingTeamName = '-';
let unsoldModeEnabled = false;

// Toggle Unsold Mode
function toggleUnsoldMode() {
    unsoldModeEnabled = document.getElementById('unsoldMode').checked;
    const modeLabel = document.getElementById('modeLabel');
    const randomizerSection = document.querySelector('.randomizer-section');
    
    if (unsoldModeEnabled) {
        modeLabel.textContent = '🔄 UNSOLD Mode (Unsold players included)';
        randomizerSection.classList.add('unsold-mode');
        showNotification('Unsold Mode ON - Unsold players are now in the pool', 'info');
    } else {
        modeLabel.textContent = 'Normal Mode';
        randomizerSection.classList.remove('unsold-mode');
        showNotification('Normal Mode - Only new players in pool', 'info');
    }
}

// Initialize auctioneer panel
function initAuctioneerPanel() {
    // Get current player ID from the page if auction is active
    const playerCard = document.getElementById('currentPlayer');
    if (playerCard && playerCard.dataset.playerId) {
        currentPlayerId = parseInt(playerCard.dataset.playerId);
    }
    
    // Get initial price from page if auction is active
    const priceEl = document.getElementById('currentPrice');
    if (priceEl && priceEl.textContent) {
        currentBidPrice = parseFloat(priceEl.textContent) || 50;
        updateBidDisplay();
    }
    
    console.log('Auctioneer Panel initialized. Current Player ID:', currentPlayerId, 'Current Price:', currentBidPrice);
}

// Fixed bid increment in Lakhs
const BID_INCREMENT = 25;

// Helper to select team from data attributes (safe for special characters)
function selectTeamFromData(btn) {
    const teamId = parseInt(btn.dataset.teamId);
    const teamName = btn.dataset.teamName;
    selectTeam(teamId, teamName);
}

// Select team for bidding - first click = base price, subsequent clicks = +25L
async function selectTeam(teamId, teamName) {
    if (!currentPlayerId) {
        showNotification('No active auction!', 'error');
        return;
    }
    
    selectedTeamId = teamId;
    selectedTeamName = teamName;
    
    // Update UI
    document.querySelectorAll('.team-btn').forEach(btn => btn.classList.remove('selected'));
    document.querySelector(`.team-btn[data-team-id="${teamId}"]`).classList.add('selected');
    document.getElementById('selectedTeamName').textContent = teamName;
    
    // Calculate bid amount:
    // - If no bids yet (leadingTeamName is '-'), bid at base price
    // - Otherwise, add 25L increment
    let newBidPrice;
    let isBasePriceBid = false;
    
    if (leadingTeamName === '-') {
        // First bid - use base price
        newBidPrice = currentBidPrice;
        isBasePriceBid = true;
    } else {
        // Subsequent bid - add increment
        newBidPrice = currentBidPrice + BID_INCREMENT;
    }
    
    const bidAmount = newBidPrice * 100000;
    
    try {
        const response = await fetch('/api/bid', {
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
            currentBidPrice = newBidPrice;
            leadingTeamName = teamName;
            updateBidDisplay();
            
            if (isBasePriceBid) {
                showNotification(`${teamName} bids ₹${newBidPrice} L (base price)`, 'success');
            } else {
                showNotification(`${teamName} bids ₹${newBidPrice} L (+${BID_INCREMENT}L)`, 'success');
            }
            addToBidHistory(teamName, newBidPrice);
        } else {
            showNotification(data.error || 'Bid failed', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error placing bid', 'error');
    }
}

// Quick bid with preset amount
function quickBid(amountInLakhs) {
    if (!selectedTeamId) {
        showNotification('Please select a team first!', 'error');
        return;
    }
    
    if (!currentPlayerId) {
        showNotification('No active auction!', 'error');
        return;
    }
    
    // Calculate new bid (current + increment)
    const newBid = currentBidPrice + amountInLakhs;
    const newBidRaw = newBid * 100000;
    
    // Place the bid
    placeBidFromPanel(selectedTeamId, newBidRaw, selectedTeamName, newBid);
}

async function placeBidFromPanel(teamId, amount, teamName, amountInLakhs) {
    try {
        const response = await fetch('/api/bid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_id: currentPlayerId,
                team_id: teamId,
                amount: amount
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentBidPrice = amountInLakhs;
            leadingTeamName = teamName;
            updateBidDisplay();
            showNotification(`${teamName} bids ₹${amountInLakhs} L!`, 'success');
            
            // Add to bid history
            addToBidHistory(teamName, amountInLakhs);
        } else {
            showNotification(data.error || 'Bid failed', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error placing bid', 'error');
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
        bidItem.style.cssText = 'padding: 0.5rem; background: #e8f5e9; margin-bottom: 0.5rem; border-radius: 3px;';
        bidItem.textContent = `${teamName}: ₹${amount} L`;
        bidList.insertBefore(bidItem, bidList.firstChild);
    }
}

function resetPrice() {
    const newPrice = parseFloat(document.getElementById('resetPriceInput').value);
    
    if (!newPrice || newPrice <= 0) {
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
    
    // Call API to persist price reset
    fetch('/api/auction/reset-price', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price: newPrice * 100000 })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentBidPrice = newPrice;
            leadingTeamName = '-';  // Reset leading team
            updateBidDisplay();
            
            // Clear the input
            document.getElementById('resetPriceInput').value = '';
            
            showNotification(`Price reset to ₹${newPrice} L`, 'success');
            
            // Add to bid history
            const bidList = document.getElementById('bidList');
            if (bidList) {
                const bidItem = document.createElement('div');
                bidItem.style.cssText = 'padding: 0.5rem; background: #fff3cd; margin-bottom: 0.5rem; border-radius: 3px; color: #856404;';
                bidItem.textContent = `⚠️ Price reset to ₹${newPrice} L`;
                bidList.insertBefore(bidItem, bidList.firstChild);
            }
        } else {
            showNotification(data.error || 'Failed to reset price', 'error');
        }
    })
    .catch(error => {
        showNotification('Error resetting price', 'error');
    });
}

async function markSold() {
    if (!currentPlayerId || leadingTeamName === '-') {
        showNotification('No valid bid to finalize!', 'error');
        return;
    }
    
    if (!confirm(`Confirm SOLD to ${leadingTeamName} for ₹${currentBidPrice >= 100 ? (currentBidPrice/100).toFixed(2) + ' Cr' : currentBidPrice + ' L'}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/auction/end', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showNotification(`SOLD to ${leadingTeamName}!`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification(data.error || 'Error ending auction', 'error');
        }
    } catch (error) {
        showNotification('Error ending auction', 'error');
    }
}

async function markUnsold() {
    if (!confirm('Mark this player as UNSOLD?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/auction/unsold', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showNotification('Player marked as UNSOLD', 'info');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification(data.error || 'Error', 'error');
        }
    } catch (error) {
        showNotification('Error marking unsold', 'error');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initAuctioneerPanel);

// Pick random player from selected position with animation
async function pickRandomPlayer() {
    const position = document.getElementById('positionFilter').value;
    const resultDiv = document.getElementById('randomResult');
    const btn = document.querySelector('.randomizer-controls button');
    
    // Disable button during animation
    btn.disabled = true;
    btn.innerHTML = '🎰 Selecting...';
    
    try {
        // Build URL with position and unsold mode
        let url = '/api/players/available';
        const params = [];
        if (position) params.push(`position=${position}`);
        if (unsoldModeEnabled) params.push('include_unsold=true');
        if (params.length > 0) url += '?' + params.join('&');
        const response = await fetch(url);
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
        const totalCycles = 20;
        let delay = 50;
        
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
                selectFinalPlayer(position, resultDiv, btn);
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

async function selectFinalPlayer(position, resultDiv, btn) {
    // Build URL with position and unsold mode
    let url = '/api/players/random';
    const params = [];
    if (position) params.push(`position=${position}`);
    if (unsoldModeEnabled) params.push('include_unsold=true');
    if (params.length > 0) url += '?' + params.join('&');
    
    const response = await fetch(url);
    const data = await response.json();
    
    resultDiv.classList.remove('spinning');
    
    if (data.success) {
        const player = data.player;
        resultDiv.innerHTML = `
            <div class="final-result">
                <div class="confetti">🎉</div>
                <h3>${escapeHtml(player.name)}</h3>
                <p>${escapeHtml(player.position)} | Base Price: ₹${player.base_price / 100000} L</p>
                <button class="btn btn-primary pulse" onclick="startAuction(${parseInt(player.id)})">Start Auction for ${escapeHtml(player.name)}</button>
            </div>
        `;
    } else {
        resultDiv.innerHTML = `<p style="color: #e74c3c;">${escapeHtml(data.error)}</p>`;
    }
    
    btn.disabled = false;
    btn.innerHTML = '🎲 Pick Random Player';
}

// Start auction for a player
async function startAuction(playerId) {
    try {
        const response = await fetch(`/api/auction/start/${playerId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Auction started!', 'success');
            currentPlayerId = playerId;
            location.reload(); // Reload to show updated state
        } else {
            showNotification('Failed to start auction', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error starting auction', 'error');
    }
}

// Place bid
document.getElementById('bidForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!currentPlayerId) {
        showNotification('No active auction', 'error');
        return;
    }
    
    const teamId = document.getElementById('teamSelect').value;
    const amountInLakhs = document.getElementById('bidAmount').value;
    const amount = parseFloat(amountInLakhs) * 100000; // Convert Lakhs to raw value
    
    try {
        const response = await fetch('/api/bid', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                player_id: currentPlayerId,
                team_id: parseInt(teamId),
                amount: amount
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Bid placed successfully!', 'success');
            document.getElementById('currentPrice').textContent = formatCurrency(data.current_price);
            
            // Add to bid history
            const bidList = document.getElementById('bidList');
            const bidItem = document.createElement('div');
            const teamName = document.getElementById('teamSelect').selectedOptions[0].text.split(' (')[0];
            bidItem.textContent = `${teamName}: ${formatCurrency(amount)}`;
            bidItem.style.padding = '0.5rem';
            bidItem.style.background = '#e8f5e9';
            bidItem.style.marginBottom = '0.5rem';
            bidItem.style.borderRadius = '3px';
            bidList.insertBefore(bidItem, bidList.firstChild);
        } else {
            showNotification(data.error || 'Failed to place bid', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error placing bid', 'error');
    }
});

// End auction
document.getElementById('endAuctionBtn')?.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to end the current auction?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/auction/end', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Auction ended!', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification(data.error || 'Failed to end auction', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error ending auction', 'error');
    }
});

// Timer countdown (simple client-side version)
let timeRemaining = parseInt(document.getElementById('timer')?.textContent) || 0;
if (timeRemaining > 0) {
    timerInterval = setInterval(() => {
        timeRemaining--;
        const timerEl = document.getElementById('timer');
        if (timerEl) {
            timerEl.textContent = timeRemaining;
            
            if (timeRemaining <= 0) {
                clearInterval(timerInterval);
                showNotification('Time is up!', 'info');
            }
        }
    }, 1000);
}
