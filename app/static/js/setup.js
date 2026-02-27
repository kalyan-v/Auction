/**
 * WPL Auction System - Setup Page
 *
 * Handles league, team, and player management:
 * - Create new leagues with custom purse amounts
 * - Tag-based auction category picker
 * - Add teams with individual budgets
 * - Add/edit/delete players with positions, countries, and base prices
 * - Modal-based player editing with XSS-safe data attributes
 *
 * All forms use secure fetch with CSRF protection.
 * Currency inputs are in Lakhs (players) or Crores (teams/leagues).
 */

// ═══════════════════════════════════════════════════════
// BID INCREMENT TIER BUILDER
// ═══════════════════════════════════════════════════════

let bidTiers = [{ threshold: 0, increment: 2500000 }]; // default: flat 25L

function renderTierRows() {
    const container = document.getElementById('tierRows');
    if (!container) return;
    container.innerHTML = '';
    bidTiers.forEach((tier, idx) => {
        const row = document.createElement('div');
        row.className = 'tier-row';
        const thresholdLakhs = tier.threshold / 100000;
        const incrementLakhs = tier.increment / 100000;
        row.innerHTML = `
            <div class="tier-field">
                <label>${idx === 0 ? 'Starting at' : 'Above'}</label>
                <div class="input-with-unit">
                    <input type="number" class="tier-threshold" value="${thresholdLakhs}" min="0" step="1" data-idx="${idx}" ${idx === 0 ? 'disabled' : ''}>
                    <span class="input-unit">L</span>
                </div>
            </div>
            <div class="tier-field">
                <label>Increment</label>
                <div class="input-with-unit">
                    <input type="number" class="tier-increment" value="${incrementLakhs}" min="1" step="1" data-idx="${idx}">
                    <span class="input-unit">L</span>
                </div>
            </div>
            <div class="tier-summary">
                ${idx === 0 ? `Base: +₹${escapeHtml(String(incrementLakhs))}L per bid` : `Above ₹${escapeHtml(formatTierThreshold(tier.threshold))}: +₹${escapeHtml(String(incrementLakhs))}L`}
            </div>
            ${idx > 0 ? `<button type="button" class="btn-remove-tier" data-idx="${idx}" title="Remove tier">&times;</button>` : '<span class="tier-spacer"></span>'}
        `;
        container.appendChild(row);
    });
}

function formatTierThreshold(val) {
    if (val >= 10000000) return (val / 10000000).toFixed(val % 10000000 === 0 ? 0 : 1) + ' Cr';
    return (val / 100000) + ' L';
}

// Add tier
document.getElementById('addTierBtn')?.addEventListener('click', () => {
    // Default: next tier at 5 Cr above last threshold with double increment
    const lastTier = bidTiers[bidTiers.length - 1];
    const newThreshold = lastTier.threshold + 50000000; // +5 Cr
    const newIncrement = lastTier.increment * 2;
    bidTiers.push({ threshold: newThreshold, increment: newIncrement });
    renderTierRows();
});

// Remove tier + update values via delegation
document.getElementById('tierRows')?.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-remove-tier');
    if (btn) {
        bidTiers.splice(parseInt(btn.dataset.idx, 10), 1);
        renderTierRows();
    }
});

document.getElementById('tierRows')?.addEventListener('change', (e) => {
    const input = e.target;
    const idx = parseInt(input.dataset.idx, 10);
    if (isNaN(idx) || idx >= bidTiers.length) return;
    if (input.classList.contains('tier-threshold')) {
        bidTiers[idx].threshold = parseFloat(input.value) * 100000;
    } else if (input.classList.contains('tier-increment')) {
        bidTiers[idx].increment = parseFloat(input.value) * 100000;
    }
    renderTierRows(); // re-render summaries
});

// Tier presets
document.querySelectorAll('.tier-preset').forEach(btn => {
    btn.addEventListener('click', () => {
        try {
            bidTiers = JSON.parse(btn.dataset.tiers);
            renderTierRows();
        } catch (e) { /* ignore */ }
    });
});

// Initialize
renderTierRows();

// ═══════════════════════════════════════════════════════
// AUCTION CATEGORY TAG MANAGEMENT
// ═══════════════════════════════════════════════════════

const categoryTags = [];

function renderCategoryTags() {
    const list = document.getElementById('categoryTagList');
    if (!list) return;
    list.innerHTML = '';
    categoryTags.forEach((tag, idx) => {
        const el = document.createElement('span');
        el.className = 'cat-tag';
        el.innerHTML = `${escapeHtml(tag)}<button type="button" class="cat-tag-remove" data-idx="${idx}" title="Remove">&times;</button>`;
        list.appendChild(el);
    });
}

function addCategoryTag(name) {
    const trimmed = name.trim();
    if (!trimmed) return;
    // Prevent duplicates (case-insensitive)
    if (categoryTags.some(t => t.toLowerCase() === trimmed.toLowerCase())) {
        showNotification(`"${trimmed}" is already added`, 'error');
        return;
    }
    categoryTags.push(trimmed);
    renderCategoryTags();
}

function removeCategoryTag(idx) {
    categoryTags.splice(idx, 1);
    renderCategoryTags();
}

// Tag input: Enter key adds tag
document.getElementById('categoryInput')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        const input = e.target;
        addCategoryTag(input.value);
        input.value = '';
    }
});

// Add button
document.getElementById('addCategoryBtn')?.addEventListener('click', () => {
    const input = document.getElementById('categoryInput');
    if (input) {
        addCategoryTag(input.value);
        input.value = '';
        input.focus();
    }
});

// Remove tag via delegation
document.getElementById('categoryTagList')?.addEventListener('click', (e) => {
    const btn = e.target.closest('.cat-tag-remove');
    if (btn) {
        removeCategoryTag(parseInt(btn.dataset.idx, 10));
    }
});

// Category preset buttons (exclude tier presets which also have .tag-preset)
document.querySelectorAll('.tag-preset[data-categories]').forEach(btn => {
    btn.addEventListener('click', () => {
        const cats = btn.dataset.categories.split(',');
        // Clear existing and set preset
        categoryTags.length = 0;
        cats.forEach(c => categoryTags.push(c.trim()));
        renderCategoryTags();
    });
});

// Add League
document.getElementById('leagueForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('leagueName')?.value?.trim();
    const displayName = document.getElementById('leagueDisplayName')?.value?.trim();
    const purseInCr = document.getElementById('leaguePurse')?.value;
    const default_purse = parseFloat(purseInCr) * 10000000;
    const league_type = document.getElementById('leagueType')?.value || 'wpl';
    const max_rtm = parseInt(document.getElementById('leagueMaxRtm')?.value || '0', 10);
    // Read from tag array instead of comma-separated text
    const auction_categories = [...categoryTags];

    if (!name || !displayName) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }

    if (isNaN(default_purse) || default_purse <= 0) {
        showNotification('Please enter a valid purse amount', 'error');
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Creating...';
    }

    try {
        const response = await secureFetch('/api/leagues', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, display_name: displayName, default_purse: default_purse, bid_increment_tiers: bidTiers, max_rtm: max_rtm, league_type: league_type, auction_categories: auction_categories })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('League created successfully!', 'success');
            window.location.href = '/switch-league/' + data.league_id + '?next=/setup';
        } else {
            showNotification(data.error || 'Failed to create league', 'error');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create League';
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error creating league', 'error');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create League';
        }
    }
});

// Add Team
document.getElementById('teamForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('teamName')?.value?.trim();
    const budgetInCr = document.getElementById('teamBudget')?.value;
    const budget = parseFloat(budgetInCr) * 10000000;

    if (!name) {
        showNotification('Please enter a team name', 'error');
        return;
    }

    if (isNaN(budget) || budget <= 0) {
        showNotification('Please enter a valid budget', 'error');
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Adding...';
    }

    try {
        const response = await secureFetch('/api/teams', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, budget: budget })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Team added successfully!', 'success');

            // Add team to list
            const teamsList = document.getElementById('teamsList');
            if (teamsList) {
                // Remove empty-state if present
                const empty = teamsList.querySelector('.empty-state');
                if (empty) empty.remove();
                const teamItem = document.createElement('div');
                teamItem.className = 'item-row';
                teamItem.innerHTML = `
                    <span class="item-name">${escapeHtml(name)}</span>
                    <span class="item-meta item-meta--money">${formatCurrency(budget)}</span>
                `;
                teamsList.appendChild(teamItem);
            }

            // Reset form
            e.target.reset();
        } else {
            showNotification(data.error || 'Failed to add team', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error adding team', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Add Team';
        }
    }
});

// Add Player
document.getElementById('playerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('playerName')?.value?.trim();
    const position = document.getElementById('playerPosition')?.value;
    const country = document.getElementById('playerCountry')?.value;
    const basePriceInLakhs = document.getElementById('playerBasePrice')?.value;
    const base_price = parseFloat(basePriceInLakhs) * 100000;
    const original_team = document.getElementById('playerOriginalTeam')?.value?.trim() || '';
    const auction_category = document.getElementById('playerAuctionCategory')?.value || '';

    if (!name) {
        showNotification('Please enter a player name', 'error');
        return;
    }

    if (!position) {
        showNotification('Please select a position', 'error');
        return;
    }

    if (isNaN(base_price) || base_price <= 0) {
        showNotification('Please enter a valid base price', 'error');
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Adding...';
    }

    try {
        const response = await secureFetch('/api/players', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                position,
                country,
                base_price: base_price,
                original_team: original_team,
                auction_category: auction_category
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Player added successfully!', 'success');

            // Add player to list using data attributes for XSS-safe editing
            const playersList = document.getElementById('playersList');
            if (playersList) {
                // Remove empty-state if present
                const empty = playersList.querySelector('.empty-state');
                if (empty) empty.remove();
                const playerItem = document.createElement('div');
                playerItem.className = 'item-row item-row--player';
                playerItem.dataset.playerId = data.player_id;
                const countryDisplay = country === 'Overseas' ? '✈️' : '🇮🇳';
                const basePriceInLakhsDisplay = base_price / 100000;
                const originalTeamDisplay = original_team ? `<span class="item-meta item-meta--team">${escapeHtml(original_team)}</span>` : '';

                // Create button with data attributes instead of inline onclick
                const editBtn = document.createElement('button');
                editBtn.className = 'btn btn-icon btn-edit';
                editBtn.textContent = '✏️';
                editBtn.dataset.playerId = data.player_id;
                editBtn.dataset.playerName = name;
                editBtn.dataset.playerPosition = position;
                editBtn.dataset.playerCountry = country;
                editBtn.dataset.playerBasePrice = base_price;
                editBtn.dataset.playerOriginalTeam = original_team || '';
                editBtn.dataset.playerAuctionCategory = auction_category || '';
                editBtn.onclick = function() { editPlayerFromData(this); };

                playerItem.innerHTML = `
                    <span class="item-name">${escapeHtml(name)}</span>
                    <span class="item-meta item-meta--position">${escapeHtml(position)}</span>
                    <span class="item-meta item-meta--country">${countryDisplay}</span>
                    <span class="item-meta item-meta--money">₹${basePriceInLakhsDisplay} L</span>
                    ${originalTeamDisplay}
                    ${auction_category ? `<span class="badge category-badge">${escapeHtml(auction_category)}</span>` : ''}
                `;
                playerItem.appendChild(editBtn);
                playersList.appendChild(playerItem);
            }

            // Reset form
            e.target.reset();
            // Re-select the disabled placeholder for position dropdown
            const positionSelect = document.getElementById('playerPosition');
            if (positionSelect) positionSelect.selectedIndex = 0;
        } else {
            showNotification(data.error || 'Failed to add player', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error adding player', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Add Player';
        }
    }
});

// Edit Player using data attributes (safe for names with special characters)
function editPlayerFromData(btn) {
    const id = btn.dataset.playerId;
    const name = btn.dataset.playerName;
    const position = btn.dataset.playerPosition;
    const country = btn.dataset.playerCountry;
    const basePrice = parseFloat(btn.dataset.playerBasePrice);
    const originalTeam = btn.dataset.playerOriginalTeam || '';
    const auctionCategory = btn.dataset.playerAuctionCategory || '';
    
    document.getElementById('editPlayerId').value = id;
    document.getElementById('editPlayerName').value = name;
    document.getElementById('editPlayerPosition').value = position;
    document.getElementById('editPlayerCountry').value = country;
    document.getElementById('editPlayerBasePrice').value = basePrice / 100000;
    document.getElementById('editPlayerOriginalTeam').value = originalTeam;
    const catSelect = document.getElementById('editPlayerAuctionCategory');
    if (catSelect) catSelect.value = auctionCategory;
    document.getElementById('editPlayerModal').style.display = 'flex';
}

// Legacy edit function (kept for compatibility)
function editPlayer(id, name, position, country, basePrice, originalTeam) {
    document.getElementById('editPlayerId').value = id;
    document.getElementById('editPlayerName').value = name;
    document.getElementById('editPlayerPosition').value = position;
    document.getElementById('editPlayerCountry').value = country;
    document.getElementById('editPlayerBasePrice').value = basePrice / 100000;
    document.getElementById('editPlayerOriginalTeam').value = originalTeam || '';
    document.getElementById('editPlayerModal').style.display = 'flex';
}

function closeEditModal() {
    const modal = document.getElementById('editPlayerModal');
    if (modal) modal.style.display = 'none';
}

// Save edited player
document.getElementById('editPlayerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const id = document.getElementById('editPlayerId')?.value;
    const name = document.getElementById('editPlayerName')?.value?.trim();
    const position = document.getElementById('editPlayerPosition')?.value;
    const country = document.getElementById('editPlayerCountry')?.value;
    const basePriceValue = document.getElementById('editPlayerBasePrice')?.value;
    const basePrice = parseFloat(basePriceValue) * 100000;
    const originalTeam = document.getElementById('editPlayerOriginalTeam')?.value?.trim() || '';
    const auctionCategory = document.getElementById('editPlayerAuctionCategory')?.value || '';

    if (!id || !name || !position) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }

    if (isNaN(basePrice) || basePrice <= 0) {
        showNotification('Please enter a valid base price', 'error');
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Saving...';
    }

    try {
        const response = await secureFetch(`/api/players/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, position, country, base_price: basePrice, original_team: originalTeam, auction_category: auctionCategory })
        });

        const data = await response.json();
        if (data.success) {
            showNotification('Player updated!', 'success');
            location.reload();
        } else {
            showNotification(data.error || 'Error updating player', 'error');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Save Changes';
            }
        }
    } catch (error) {
        showNotification('Error updating player', 'error');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Save Changes';
        }
    }
});

// Delete player
let isDeletingPlayer = false;
async function deletePlayer() {
    if (isDeletingPlayer) return;
    if (!confirm('Are you sure you want to delete this player?')) return;

    const id = document.getElementById('editPlayerId')?.value;
    if (!id) {
        showNotification('No player selected', 'error');
        return;
    }

    isDeletingPlayer = true;

    // Find and disable delete button
    const deleteBtn = document.querySelector('#editPlayerForm .btn-danger');
    if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.textContent = '⏳ Deleting...';
    }

    try {
        const response = await secureFetch(`/api/players/${id}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.success) {
            showNotification('Player deleted!', 'success');
            location.reload();
        } else {
            showNotification(data.error || 'Error deleting player', 'error');
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.textContent = 'Delete Player';
            }
            isDeletingPlayer = false;
        }
    } catch (error) {
        showNotification('Error deleting player', 'error');
        if (deleteBtn) {
            deleteBtn.disabled = false;
            deleteBtn.textContent = 'Delete Player';
        }
        isDeletingPlayer = false;
    }
}

// Close modal on outside click
window.addEventListener('click', (e) => {
    const modal = document.getElementById('editPlayerModal');
    if (modal && e.target === modal) closeEditModal();
});

// Close modal on ESC key and trap focus
document.addEventListener('keydown', (e) => {
    const modal = document.getElementById('editPlayerModal');
    if (modal && modal.style.display === 'flex') {
        if (e.key === 'Escape') {
            closeEditModal();
        }
        // Trap focus within modal
        if (e.key === 'Tab') {
            const focusableElements = modal.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            if (e.shiftKey && document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            } else if (!e.shiftKey && document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    }
});