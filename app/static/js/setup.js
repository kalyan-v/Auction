// Setup page functionality

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
                <span>${name}</span>
                <span class="budget">${formatCurrency(budget)}</span>
            `;
            teamsList.appendChild(teamItem);
            
            // Reset form
            e.target.reset();
        } else {
            showNotification('Failed to add team', 'error');
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
                base_price: base_price 
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Player added successfully!', 'success');
            
            // Add player to list
            const playersList = document.getElementById('playersList');
            const playerItem = document.createElement('div');
            playerItem.className = 'list-item';
            playerItem.dataset.playerId = data.player_id;
            const countryDisplay = country === 'Overseas' ? '<span class="country-emoji">✈️</span>' : '<span class="flag-india"></span>';
            const basePriceInLakhs = base_price / 100000;
            playerItem.innerHTML = `
                <span class="player-name">${name}</span>
                <span class="position">${position}</span>
                <span>${countryDisplay}</span>
                <span class="price">₹${basePriceInLakhs} L</span>
                <button class="btn btn-small btn-edit" onclick="editPlayer(${data.player_id}, '${name}', '${position}', '${country}', ${base_price})">✏️</button>
            `;
            playersList.appendChild(playerItem);
            
            // Reset form
            e.target.reset();
        } else {
            showNotification('Failed to add player', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error adding player', 'error');
    }
});

// Edit Player
function editPlayer(id, name, position, country, basePrice) {
    document.getElementById('editPlayerId').value = id;
    document.getElementById('editPlayerName').value = name;
    document.getElementById('editPlayerPosition').value = position;
    document.getElementById('editPlayerCountry').value = country;
    document.getElementById('editPlayerBasePrice').value = basePrice / 100000;
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
    
    try {
        const response = await fetch(`/api/players/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, position, country, base_price: basePrice })
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