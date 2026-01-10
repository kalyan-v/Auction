// Setup page functionality

// Add League
document.getElementById('leagueForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('leagueName').value;
    const displayName = document.getElementById('leagueDisplayName').value;
    const purseInCr = document.getElementById('leaguePurse').value;
    const default_purse = parseFloat(purseInCr) * 10000000; // Convert Crores to raw value
    
    try {
        const response = await fetch('/api/leagues', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, display_name: displayName, default_purse: default_purse })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('League created successfully!', 'success');
            // Switch to the new league and reload
            window.location.href = '/switch-league/' + data.league_id + '?next=/setup';
        } else {
            showNotification(data.error || 'Failed to create league', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error creating league', 'error');
    }
});

// Add Team
document.getElementById('teamForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('teamName').value;
    const budgetInCr = document.getElementById('teamBudget').value;
    const budget = parseFloat(budgetInCr) * 10000000; // Convert Crores to raw value
    
    try {
        const response = await fetch('/api/teams', {
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
            const teamItem = document.createElement('div');
            teamItem.className = 'list-item';
            teamItem.innerHTML = `
                <span>${escapeHtml(name)}</span>
                <span class="budget">${formatCurrency(budget)}</span>
            `;
            teamsList.appendChild(teamItem);
            
            // Reset form
            e.target.reset();
        } else {
            showNotification(data.error || 'Failed to add team', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error adding team', 'error');
    }
});

// Add Player
document.getElementById('playerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('playerName').value;
    const position = document.getElementById('playerPosition').value;
    const country = document.getElementById('playerCountry').value;
    const basePriceInLakhs = document.getElementById('playerBasePrice').value;
    const base_price = parseFloat(basePriceInLakhs) * 100000; // Convert Lakhs to raw value
    const original_team = document.getElementById('playerOriginalTeam')?.value || '';
    
    try {
        const response = await fetch('/api/players', {
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
            
            // Reset form
            e.target.reset();
        } else {
            showNotification(data.error || 'Failed to add player', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error adding player', 'error');
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
    document.getElementById('editPlayerModal').style.display = 'none';
}

// Save edited player
document.getElementById('editPlayerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('editPlayerId').value;
    const name = document.getElementById('editPlayerName').value;
    const position = document.getElementById('editPlayerPosition').value;
    const country = document.getElementById('editPlayerCountry').value;
    const basePrice = parseFloat(document.getElementById('editPlayerBasePrice').value) * 100000;
    const originalTeam = document.getElementById('editPlayerOriginalTeam')?.value || '';
    
    try {
        const response = await fetch(`/api/players/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, position, country, base_price: basePrice, original_team: originalTeam })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Player updated!', 'success');
            location.reload();
        } else {
            showNotification('Error updating player', 'error');
        }
    } catch (error) {
        showNotification('Error updating player', 'error');
    }
});

// Delete player
async function deletePlayer() {
    if (!confirm('Are you sure you want to delete this player?')) return;
    
    const id = document.getElementById('editPlayerId').value;
    
    try {
        const response = await fetch(`/api/players/${id}`, { method: 'DELETE' });
        const data = await response.json();
        
        if (data.success) {
            showNotification('Player deleted!', 'success');
            location.reload();
        } else {
            showNotification('Error deleting player', 'error');
        }
    } catch (error) {
        showNotification('Error deleting player', 'error');
    }
}

// Close modal on outside click
window.addEventListener('click', (e) => {
    const modal = document.getElementById('editPlayerModal');
    if (e.target === modal) closeEditModal();
});