/**
 * WPL Auction System - Setup Page
 *
 * Handles league, team, and player management:
 * - Create new leagues with custom purse amounts
 * - Add teams with individual budgets
 * - Add/edit/delete players with positions, countries, and base prices
 * - Modal-based player editing with XSS-safe data attributes
 *
 * All forms use secure fetch with CSRF protection.
 * Currency inputs are in Lakhs (players) or Crores (teams/leagues).
 */

// Add League
document.getElementById('leagueForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('leagueName')?.value?.trim();
    const displayName = document.getElementById('leagueDisplayName')?.value?.trim();
    const purseInCr = document.getElementById('leaguePurse')?.value;
    const default_purse = parseFloat(purseInCr) * 10000000;

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
            body: JSON.stringify({ name, display_name: displayName, default_purse: default_purse })
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
                const teamItem = document.createElement('div');
                teamItem.className = 'list-item';
                teamItem.innerHTML = `
                    <span>${escapeHtml(name)}</span>
                    <span class="budget">${formatCurrency(budget)}</span>
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
                original_team: original_team
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Player added successfully!', 'success');

            // Add player to list using data attributes for XSS-safe editing
            const playersList = document.getElementById('playersList');
            if (playersList) {
                const playerItem = document.createElement('div');
                playerItem.className = 'list-item';
                playerItem.dataset.playerId = data.player_id;
                const countryDisplay = country === 'Overseas' ? '<span class="country-emoji">✈️</span>' : '<span class="flag-india"></span>';
                const basePriceInLakhsDisplay = base_price / 100000;
                const originalTeamDisplay = original_team ? `<span class="original-team">${escapeHtml(original_team)}</span>` : '';

                // Create button with data attributes instead of inline onclick
                const editBtn = document.createElement('button');
                editBtn.className = 'btn btn-small btn-edit';
                editBtn.textContent = '✏️';
                editBtn.dataset.playerId = data.player_id;
                editBtn.dataset.playerName = name;
                editBtn.dataset.playerPosition = position;
                editBtn.dataset.playerCountry = country;
                editBtn.dataset.playerBasePrice = base_price;
                editBtn.dataset.playerOriginalTeam = original_team || '';
                editBtn.onclick = function() { editPlayerFromData(this); };

                playerItem.innerHTML = `
                    <span class="player-name">${escapeHtml(name)}</span>
                    <span class="position">${escapeHtml(position)}</span>
                    <span>${countryDisplay}</span>
                    <span class="price">₹${basePriceInLakhsDisplay} L</span>
                    ${originalTeamDisplay}
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
    
    document.getElementById('editPlayerId').value = id;
    document.getElementById('editPlayerName').value = name;
    document.getElementById('editPlayerPosition').value = position;
    document.getElementById('editPlayerCountry').value = country;
    document.getElementById('editPlayerBasePrice').value = basePrice / 100000;
    document.getElementById('editPlayerOriginalTeam').value = originalTeam;
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
            body: JSON.stringify({ name, position, country, base_price: basePrice, original_team: originalTeam })
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

// Close modal on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('editPlayerModal');
        if (modal && modal.style.display !== 'none') {
            closeEditModal();
        }
    }
});