const API_PATH = '/api';

onload = () => {
    const radios = document.querySelectorAll('input[name="winners"]');
    const submitBtn = document.getElementById('submit-round');

    radios.forEach(radio => {
        radio.addEventListener('change', () => {
            submitBtn.disabled = false;
        });
    });
}

async function createGame() {
    const gameID = prompt("Enter a unique game ID:");
    if (!gameID) return;

    const playersInput = prompt("Enter player names separated by commas (e.g., Alice,Bob,Charlie):");
    const playerNames = playersInput ? playersInput.split(',').map(name => name.trim()).filter(name => name) : [];

    try {
        const response = await fetch(API_PATH + `/games/${gameID}/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                playerNames: playerNames
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || response.statusText;
            throw new Error(`HTTP Error ${response.status}: ${errorMessage}`);
        }

        const data = await response.json();
        if (data.success) {
            console.log(`Game "${gameID}" created successfully.`);
            document.getElementById("game-selector").value = gameID;
        } else {
            throw new Error(`API Error: ${data.message || 'Unknown backend error'}`);
        }
    } catch (e) {
        console.error(e);
    }
}


async function loadGame() {
    const data = await _fetchGameFile();
    _loadGameData(data.gameData);
    _loadNextRoundData(data.gameData);
}


async function _fetchGameFile() {
    console.log("Fetching game status...");

    try {
        let gameID = document.getElementById("game-selector").value;

        if (gameID.trim() === "") {
            throw new Error("No game ID selected.");
        }

        const response = await fetch(API_PATH + `/games/${gameID}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({})); 
            const errorMessage = errorData.detail || response.statusText;
            throw new Error(`HTTP Error ${response.status}: ${errorMessage}`);
        }

        const data = await response.json();

        if (data.success) {
            console.log(`Game "${gameID}" data received successfully.`);
            return data;
        } else {
            throw new Error(`API Error: ${data.message || 'Unknown backend error'}`);
        }

    } catch (e) {
        console.error(e);
    }

}

async function _loadGameData(gameData) {
    // Hide the landing view and show the game view
    document.getElementById("landing").classList.add("hidden");
    document.getElementById("game").classList.remove("hidden");
    
    // Set game name in the UI
    document.getElementById("game-name").textContent = gameData.id;

    // Clear existing content in leaderboard
    let leaderboardElements = document.querySelectorAll(".leaderboard-entry");
    for (let i = 0; i < leaderboardElements.length; i++) {
        leaderboardElements[i].remove();
    }
    
    // Sort players by score
    gameData.players.sort((a, b) => b.points - a.points);
    gameData.players.forEach((player, index) => {
        player.rank = index; // Assign rank based on sorted order
    });

    // Populate the leaderboard with the received game data
    for (let i = 0; i < gameData.players.length; i++) {

        const newRow = document.createElement("tr");
        newRow.classList.add("leaderboard-entry");
        newRow.innerHTML = `
            <td class="rank"></td>
            <td class="user"><span class="username"></span></td>
            <td class="score"></td>
        `;
        document.querySelector(".leaderboard tbody").appendChild(newRow);

        // Display rank starting from 1
        document.querySelectorAll(".leaderboard-entry .rank")[i].textContent = gameData.players[i].rank + 1;
        document.querySelectorAll(".leaderboard-entry .username")[i].textContent = gameData.players[i].id;
        const formattedScore = (gameData.players[i].points * 1000)
            .toFixed(2)
            .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
        document.querySelectorAll(".leaderboard-entry .score")[i].textContent = formattedScore;
    }
}

async function _loadNextRoundData(gameData) {
    // Clear existing content
    document.querySelectorAll(".player-entry").forEach(el => el.remove());

    // Sort by alphabetical order of player IDs
    gameData.players.sort((a, b) => a.id.localeCompare(b.id));

    // Populate the next round data with the received game data  
    for (let i = 0; i < gameData.players.length; i++) {
        const playerId = gameData.players[i].id; 

        const newPlayer = _createNewPlayerEntry(playerId, gameData.players[i].active, gameData.players[i].role);
        
        document.querySelector("#player-manager").appendChild(newPlayer);
    }
}

function _createNewPlayerEntry(playerId) {
    const newPlayer = document.createElement("div");
    newPlayer.classList.add("player-entry");
    newPlayer.setAttribute("data-player-id", playerId);
    
    newPlayer.innerHTML = `
        <span class="player-name">${playerId}</span>

        <label for="active_${playerId}">Active:</label>
        <input type="checkbox" id="active_${playerId}" name="players[${playerId}][active]" value="true" checked>

        <label for="role_${playerId}">Ruolo:</label>
        <select id="role_${playerId}" name="players[${playerId}][role]">
            <option value=0>Buono</option>
            <option value=1>Cattivo</option>
            <option value=2>Folle</option>
            <option value=3>Criceto mannaro (NON convertito)</option>
            <option value=4>Criceto mannaro (convertito)</option>
        </select>
    `;
    
    return newPlayer;
}

async function backToLanding() {
    // Hide the game view and show the landing view
    document.getElementById("game").classList.add("hidden");
    document.getElementById("landing").classList.remove("hidden");
}

////////////////////////////////////////////////////////////////////////////////////// 
// Next round elaboration and submission
////////////////////////////////////////////////////////////////////////////////////// 

async function updateRound() {
    const gameID = document.getElementById("game-name").textContent;
    const payload = {}
    
    const playersData = {};
    document.querySelectorAll(".player-entry").forEach(playerEntry => {
        const playerId = playerEntry.getAttribute("data-player-id");
        const isActive = playerEntry.querySelector(`#active_${playerId}`).checked;
        const role = parseInt(playerEntry.querySelector(`#role_${playerId}`).value, 10);

        playersData[playerId] = {
            active: isActive,
            role: role
        };
    });
    payload.players = playersData;

    payload.roundWonBy = parseInt(document.querySelector('input[name="winners"]:checked')?.value, 10);

    console.log(`Submitting next round data for game ${gameID}:`);
    console.log(payload);

    // Send the payload to the backend
    fetch(API_PATH + `/games/${gameID}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ players: playersData, roundWonBy: payload.roundWonBy })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`Next round data for game ${gameID} submitted successfully.`);
            loadGame();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            throw new Error(`API Error: ${data.message || 'Unknown backend error'}`);
        }
    })
    .catch(e => {
        console.error(e);
    });
}


function addPlayer() {
    const playerManager = document.getElementById("player-manager");
    const newPlayerId = prompt("Enter the new player's ID:");

    if (newPlayerId) {
        // Check if the player already exists
        const existingPlayer = document.querySelector(`.player-entry[data-player-id="${newPlayerId}"]`);
        if (existingPlayer) {
            alert(`Player with ID "${newPlayerId}" already exists.`);
            return;
        }

        const newPlayerEntry = _createNewPlayerEntry(newPlayerId);
        playerManager.appendChild(newPlayerEntry);

        // Add the new player to the backend
        const gameID = document.getElementById("game-name").textContent;
        fetch(API_PATH + `/games/${gameID}/add_player`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ playerName: newPlayerId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`Player "${newPlayerId}" added to game "${gameID}" successfully.`);
            } else {
                throw new Error(`API Error: ${data.message || 'Unknown backend error'}`);
            }

            loadGame(); // Refresh the game data to reflect the new player
        })
        .catch(e => {
            console.error(e);
        });
    }
}