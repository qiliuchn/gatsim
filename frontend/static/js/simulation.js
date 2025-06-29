// Revised simulation.js with 3-second message display
(() => {
  // Simulation state
  let isRunning = false;
  let isConfigured = false;
  let updateInterval = null;
  let mapMeta = null;
  let staticEntities = {};
  const avatarPositions = {};
  
  // Track active messages and their timeouts
  const activeMessages = {};      // {personaName: {content: string, timeout: timeoutId}}
  const messageHistory = {};      // {personaName: lastMessage}
  const messageTimeHistory = {};      // {personaName: lastMessage}

  // DOM Elements
  const startButton      = document.getElementById('start-button');
  const stopButton       = document.getElementById('stop-button');
  const submitButton     = document.getElementById('submit-button');
  const forkNameInput    = document.getElementById('fork-name');
  const simNameInput     = document.getElementById('sim-name-input');
  const cmdInput         = document.getElementById('cmd-input');
  const mapOverlay       = document.getElementById('map-overlay');
  const entitySelect     = document.getElementById('entity-select');
  const entityList       = document.getElementById('entity-list');
  const simNameLabel     = document.getElementById('sim-name');
  const simStepLabel     = document.getElementById('sim-step');
  const simTimeLabel     = document.getElementById('sim-time');
  const populationContainer = document.getElementById('population-container');

  document.addEventListener('DOMContentLoaded', async () => {
    initializeButtonStates();
    await loadStaticData();
    populatePopulationSection();
    entitySelect.addEventListener('change', displayEntityInfo);
  });

  function initializeButtonStates() {
    startButton.disabled  = true;
    stopButton.disabled   = true;
    submitButton.disabled = false;
  }

  async function loadStaticData() {
    try {
      // Load map metadata and static files
      const [metaRes, facilitiesRes, nodesRes, linksRes, popRes] =
        await Promise.all([
          fetch('/static/map/maze_meta.json'),
          fetch('/static/map/facilities_info.json'),
          fetch('/static/map/nodes_info.json'),
          fetch('/static/map/links_info.json'),
          fetch('/static/agent/population_info.json')
        ]);
      mapMeta = await metaRes.json();
      staticEntities.facilities = await facilitiesRes.json();
      staticEntities.nodes      = await nodesRes.json();
      staticEntities.links      = await linksRes.json();
      staticEntities.population = await popRes.json();
      // Fill entity-select options dynamically
      ['facilities','nodes','links'].forEach(type => {
        const opt = document.createElement('option');
        opt.value = type;
        opt.textContent = type.charAt(0).toUpperCase() + type.slice(1);
        entitySelect.append(opt);
      });
    } catch (err) {
      console.error('Error loading static data', err);
      alert('Failed to load simulation metadata. Check console for details.');
    }
  }

  submitButton.addEventListener('click', submitSimulation);
  startButton.addEventListener('click',  startSimulation);
  stopButton.addEventListener('click',   stopSimulation);

  async function submitSimulation() {
    const payload = {
      fork_name: forkNameInput.value.trim() || 'none',
      simulation_name: simNameInput.value.trim(),
      command: cmdInput.value.trim() || 'run 1 day'
    };
    try {
      const res = await fetch('/submit/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === 'success') {
        isConfigured = true;
        startButton.disabled = false;
        submitButton.disabled = true;
        //showAlert(`✔ Simulation configured: ${data.message}`);
      } else {
        showAlert(`✖ Failed to configure: ${data.message}`);
      }
    } catch (err) {
      console.error(err);
      showAlert(`✖ Error submitting config: ${err.message}`);
    }
  }

  async function startSimulation() {
    if (!isConfigured) return showAlert('Please submit configuration first.');
    try {
      const res = await fetch('/run/', {method: 'POST'});
      const data = await res.json();
      if (data.status === 'success') {
        isRunning = true;
        startButton.disabled  = true;
        stopButton.disabled   = false;
        submitButton.disabled = true;
        updateInterval = setInterval(fetchSimulationData, 1000);
      } else {
        showAlert(`✖ Failed to start: ${data.message}`);
      }
    } catch (err) {
      console.error(err);
      showAlert('✖ Error starting simulation.');
    }
  }

  async function stopSimulation() {
    try {
      const res = await fetch('/stop/', {method: 'POST'});
      const data = await res.json();
      if (data.status === 'success') {
        isRunning = false;
        isConfigured = false;
        clearInterval(updateInterval);
        clearAllMessageTimeouts();
        initializeButtonStates();
      } else {
        showAlert(`✖ Failed to stop: ${data.message}`);
      }
    } catch (err) {
      console.error(err);
      showAlert('✖ Error stopping simulation.');
    }
  }

  async function fetchSimulationData() {
    try {
      const res = await fetch('/data/');
      const { meta, mobility_events, queues, curr_plans, curr_messages } = await res.json();
      updateSimulationInfo(meta);
      updateMap(mobility_events, curr_messages, queues);
      updatePopulationPlans(curr_plans);
    } catch (err) {
      console.error('Fetch data error:', err);
    }
  }

  function updateSimulationInfo({ simulation_name, curr_step, curr_time }) {
    simNameLabel.textContent = simulation_name;
    simStepLabel.textContent = curr_step;
    simTimeLabel.textContent = curr_time;
  }

  // Function to clear all message timeouts
  function clearAllMessageTimeouts() {
    Object.values(activeMessages).forEach(msg => {
      if (msg.timeout) {
        clearTimeout(msg.timeout);
      }
    });
    Object.keys(activeMessages).forEach(key => delete activeMessages[key]);
  }

  // Function to remove speech bubble after some seconds
  function removeSpeechBubbleAfterDelay(personaName, bubble, delay = 4000) {
    if (activeMessages[personaName] && activeMessages[personaName].timeout) {
      clearTimeout(activeMessages[personaName].timeout);
    }
    
    const timeout = setTimeout(() => {
      if (bubble && bubble.parentNode) {
        bubble.parentNode.removeChild(bubble);
      }
      delete activeMessages[personaName];
    }, delay);
    
    return timeout;
  }
  
function positionSpeechBubble(bubble, px, py, container) {
  // 1) Initial placement centered above (you can tweak the 17px)
  bubble.style.transform = 'translate(-50%, calc(-100% - 17px))';
  bubble.style.left      = `${px}px`;
  bubble.style.top       = `${py}px`;
  container.appendChild(bubble);

  // 2) Measure
  const bubbleRect    = bubble.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();

  // 3) Prepare for adjustments
  let adjustedX = px;
  let adjustedY = py;
  let transform = 'translate(-50%, calc(-100% - 17px))';
  const margin = 0;

  // 4) Horizontal bounds check
  const bubbleLeft  = adjustedX - bubbleRect.width  / 2;
  const bubbleRight = adjustedX + bubbleRect.width  / 2;
  if (bubbleRight > containerRect.width - margin) {
    const overflow = bubbleRight - (containerRect.width - margin);
    adjustedX = px - overflow;
  } else if (bubbleLeft < margin) {
    const overflow = margin - bubbleLeft;
    adjustedX = px + overflow;
  }

  // 5) Recompute tail position in px so it points at px
  //    newBubbleLeft is the x-coord of the left edge after adjustment
  const newBubbleLeft = adjustedX - bubbleRect.width / 2;
  const localX        = px - newBubbleLeft;
  const tailPosition  = `${localX}px`;

  // 6) Vertical bounds check: if there isn’t room above, flip below
  const bubbleTop = adjustedY - bubbleRect.height - 15; 
  if (bubbleTop < 0) {
    transform = 'translate(-50%, 5px)';  // tail now points up
    bubble.classList.add('below');
  } else {
    bubble.classList.remove('below');
  }

  // 7) Apply all final styles
  bubble.style.left      = `${adjustedX}px`;
  bubble.style.top       = `${adjustedY}px`;
  bubble.style.transform = transform;
  bubble.style.setProperty('--tail-position', tailPosition);
}


function positionSpeechBubble(bubble, px, py, container) {
  // 0) let it spill outside if needed
  container.style.overflow = 'visible';

  // 1) center on px, lift above by its own height + gap
  bubble.style.left      = `${px}px`;
  bubble.style.top       = `${py}px`;
  bubble.style.transform = 'translate(-50%, calc(-100% - 17px))'; 
  //             ↑ tweak 17px to adjust vertical gap

  // 2) point the tail dead-center
  //    since we’re never shifting horizontally, '50%' always lands it under px
  bubble.style.setProperty('--tail-position', '50%');

  // 3) add it to the DOM
  container.appendChild(bubble);
}


  // Function to calculate offset for overlapping avatars
  function calculateAvatarOffset(personas, index, tileX, tileY) {
    // Offset is added to the avatar's position to avoid overlap!!
    const avatarSize = 24;
    const radius = avatarSize * 1.5 * ((index % 4) * 0.25);  // radius of the circle; configurable parameter
    const angle = (Math.PI * 4 / personas.length) * index;
    
    // Base position
    const px = tileX * mapMeta.sq_tile_size;
    const py = tileY * mapMeta.sq_tile_size;
    
    // If only one person at this position, return center
    if (personas.length === 1) {
      return [px, py];
    }
    
    // Calculate offset for multiple personas
    const offsetX = Math.cos(angle) * radius;
    const offsetY = Math.sin(angle) * radius;
    
    return [px + offsetX, py + offsetY];
  }

  // Create avatar wrapper with avatar and tooltip
  function createAvatarWithTooltip(evt, offsetX, offsetY) {
    const { name, description } = evt;
    
    // Create wrapper for positioning
    const wrapper = document.createElement('div');
    wrapper.className = 'avatar-wrapper';
    wrapper.style.left = offsetX + 'px';
    wrapper.style.top = offsetY + 'px';
    
    // Create avatar image
    const avatar = document.createElement('img');
    avatar.src = chooseAvatar(staticEntities.population[name]);
    avatar.className = 'avatar';
    
    // Create tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'avatar-tooltip';
    tooltip.innerHTML = `
      <div class="tooltip-name">${name}</div>
      <div class="tooltip-description">${description || 'No description'}</div>
    `;
    
    // Assemble the elements
    wrapper.appendChild(avatar);
    wrapper.appendChild(tooltip);
    
    return wrapper;
  }

  // Function to detect overlapping speech bubbles
  function detectOverlappingBubbles(bubbles) {
    bubbles.forEach((bubble, index) => {
      const bubbleRect = bubble.getBoundingClientRect();
      let hasOverlap = false;
      
      bubbles.forEach((otherBubble, otherIndex) => {
        if (index !== otherIndex) {
          const otherRect = otherBubble.getBoundingClientRect();
          
          // Check if bubbles overlap
          if (!(bubbleRect.right < otherRect.left || 
                bubbleRect.left > otherRect.right || 
                bubbleRect.bottom < otherRect.top || 
                bubbleRect.top > otherRect.bottom)) {
            hasOverlap = true;
          }
        }
      });
      
      if (hasOverlap) {
        bubble.classList.add('overlapping');
      }
    });
  }

  // Updated updateMap function
  function updateMap(mobility, messages, queues) {
    // Clear previous overlays
    mapOverlay.innerHTML = '';
    
    // Group personas by their tile coordinates
    const personasByTile = {};
    Object.values(mobility).forEach(evt => {
      const [tileX, tileY] = evt.coord;
      const key = `${tileX},${tileY}`;
      if (!personasByTile[key]) {
        personasByTile[key] = [];
      }
      personasByTile[key].push(evt);
    });
    
    // 1) Draw each avatar with offset positioning
    const speechBubbles = [];
    Object.values(personasByTile).forEach(personas => {
      const [tileX, tileY] = personas[0].coord;
      
      personas.forEach((evt, index) => {
        const [offsetX, offsetY] = calculateAvatarOffset(personas, index, tileX, tileY);
        
        // Create avatar with tooltip
        const avatarWithTooltip = createAvatarWithTooltip(evt, offsetX, offsetY);
        mapOverlay.appendChild(avatarWithTooltip);
        
        // Handle speech bubble messages
        const currentMessage = messages[evt.name];
        const lastMessage = messageHistory[evt.name];
        const lastMessageTime = messageTimeHistory[evt.name];
        
        // If there's a message and it's different from the last one
        if (currentMessage && (currentMessage !== lastMessage || !lastMessageTime || (Date.now() - lastMessageTime < 4000))) {
          // If there's an existing bubble, remove it
          if (activeMessages[evt.name] && activeMessages[evt.name].bubble) {
            const oldBubble = activeMessages[evt.name].bubble;
            if (oldBubble.parentNode) {
              oldBubble.parentNode.removeChild(oldBubble);
            }
            if (activeMessages[evt.name].timeout) {
              clearTimeout(activeMessages[evt.name].timeout);
            }
          }
          
          // Create new speech bubble
          const bubble = document.createElement('div');
          bubble.className = 'speech-bubble';
          bubble.textContent = currentMessage;
          bubble.dataset.personaName = evt.name;
          
          // Position the bubble
          positionSpeechBubble(bubble, offsetX, offsetY, mapOverlay);
          speechBubbles.push(bubble);
          
          // Set up removal after some seconds
          const timeout = removeSpeechBubbleAfterDelay(evt.name, bubble);
          
          // Store the bubble and timeout
          activeMessages[evt.name] = {
            content: currentMessage,
            bubble: bubble,
            timeout: timeout
          };
          
          // Update message history
          if (currentMessage && currentMessage !== lastMessage)
          {
          messageHistory[evt.name] = currentMessage;
          messageTimeHistory[evt.name] = Date.now();
          };
        }
      });
    });
    
    // 2) Detect overlapping speech bubbles and add overlapping class
    if (speechBubbles.length > 1) {
      detectOverlappingBubbles(speechBubbles);
    }
    
  }



  


  // 1) your manifest of files per folder
  const avatarFiles = {
    boy:         [ 'boy1.png',  'boy2.png',  'boy3.png'  ],
    girl:        [ 'girl1.png', 'girl2.png', 'girl3.png' ],
    young_man:   [ 'ym1.png',   'ym2.png',   'ym3.png',   'ym4.png', 'ym5.png'   ],
    young_woman: [ 'yw1.png',   'yw2.png',   'yw3.png',   'yw4.png', 'yw5.png'   ],
    old_man:     [ 'om1.png',   'om2.png',   'om3.png'   ],
    old_woman:   [ 'ow1.png',   'ow2.png',   'ow3.png'   ],
    default:     [ 'default1.png']
  };

// 2) loader/saver for the assignments map
const STORAGE_KEY = 'avatarAssignments';
let avatarAssignments = {};
try {
  avatarAssignments = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
} catch(e) {
  avatarAssignments = {};
}

// 3) helper to pick one at random from a folder
function randomFromFolder(category) {
  const list = avatarFiles[category] || avatarFiles.default;
  const name = list[Math.floor(Math.random() * list.length)];
  return `/static/characters/${category}/${name}`;
}

// 4) your new chooseAvatar
function chooseAvatar(person) {
  if (!person) {
    // default persona
    if (!avatarAssignments.__default) {
      avatarAssignments.__default = randomFromFolder('default');
      localStorage.setItem(STORAGE_KEY, JSON.stringify(avatarAssignments));
    }
    return avatarAssignments.__default;
  }

  // identify by a stable key (e.g. person.id or person.name)
  const key = person.id ?? person.name;
  if (!key) {
    // fallback if no stable identifier
    return randomFromFolder('default');
  }

  // if we’ve already picked for this key, reuse it
  if (avatarAssignments[key]) {
    return avatarAssignments[key];
  }

  // otherwise pick category
  const { age, gender } = person;
  let category;
  if (age < 18 && gender === 'male')   category = 'boy';
  else if (age < 18 && gender === 'female') category = 'girl';
  else if (age < 50 && gender === 'male')   category = 'young_man';
  else if (age < 50 && gender === 'female') category = 'young_woman';
  else if (gender === 'male')               category = 'old_man';
  else if (gender === 'female')             category = 'old_woman';
  else                                      category = 'default';

  // pick one, store it, persist it
  const chosen = randomFromFolder(category);
  avatarAssignments[key] = chosen;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(avatarAssignments));
  return chosen;
}





  function findEntityInfo(name) {
    for (const type of ['facilities','nodes','links']) {
      if (staticEntities[type][name]) return staticEntities[type][name];
    }
    return null;
  }

  function populatePopulationSection() {
    const slug = name => name.replace(/\s+/g,'_').toLowerCase();
  
    Object.values(staticEntities.population).forEach(person => {
      const wrapper   = document.createElement('div');
      wrapper.className = 'persona-info';
  
      // — Static info —
      const staticDiv = document.createElement('div');
      staticDiv.className = 'persona-static';
  
      // Always show the name
      let html = `<h4>${person.name}</h4>`;
  
      // Pick whichever fields you want.  Here's an example list:
      const fieldsToShow = [
        'gender',
        'age',
        'highest_level_of_education',
        'family_role',
        'licensed_driver',
        'home_facility',
        'work_facility',
        'work_time',
        'occupation',
        'household_size',
        'number_of_vehicles_in_family',
        'preferences_in_transportation',
        'innate',
        'lifestyle',
        'other_family_members',
        'friends',
        'other description'
      ];
  
      fieldsToShow.forEach(key => {
        if (person[key] !== undefined) {
          // turn "licensed_driver" → "Licensed Driver"
          const label = key
            .replace(/_/g,' ')
            .replace(/\b\w/g, m => m.toUpperCase());
          //html += `<p><strong>${label}:</strong> ${person[key]}</p>`;

          // handle dictionary values
          let value = person[key];
          if (typeof value === 'object') {
            try {
              value = JSON.stringify(value, null, 4)  // or use a custom formatter
                .replace(/^{|}$/g, '')                // remove outer braces
                .replace(/"([^"]+)":/g, '<br>&nbsp;&nbsp;<strong>$1:</strong>') // indent keys
                .replace(/"/g, '');                   // strip remaining quotes
            } catch (e) {
              value = '[Object]';
            }
          }
          html += `<p><strong>${label}:</strong> ${value}</p>`;

        }
      });
  
      staticDiv.innerHTML = html;
  
      // — Plans block —
      const plansDiv = document.createElement('div');
      plansDiv.className = 'persona-plans';
      const id = `plans-${slug(person.name)}`;      // no spaces
      plansDiv.id = id;
      plansDiv.innerHTML = '<h4>Current Plan</h4><ul></ul>';
  
      wrapper.append(staticDiv, plansDiv);
      populationContainer.append(wrapper);
    });
  }

  function updatePopulationPlans(plans) {
    const slug = name => name.replace(/\s+/g,'_').toLowerCase();
  
    Object.entries(plans).forEach(([name, planList]) => {
      const containerDiv = document.getElementById(`plans-${slug(name)}`);
      if (!containerDiv) return;
  
      const ul = containerDiv.querySelector('ul');
      ul.innerHTML = '';
  
      if (!planList || planList.length === 0) {
        // optional: show a placeholder
        const li = document.createElement('li');
        li.textContent = 'No current plan';
        ul.append(li);
        return;
      }
  
      planList.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item[0]} @ ${item[1]} (${item[3]}) – ${item[5]}`;
        ul.append(li);
      });
    });
  }

  function displayEntityInfo() {
    const type = entitySelect.value;
    entityList.innerHTML = '';
    if (!type) return;
    Object.entries(staticEntities[type]).forEach(([name, info]) => {
      const div = document.createElement('div');
      div.className = 'entity-item';
      div.innerHTML = `<strong>${name}</strong><pre>${JSON.stringify(info, null, 2)}</pre>`;
      entityList.append(div);
    });
  }

  function showAlert(msg) {
    // Replace alert() with custom UI or toast in the future
    alert(msg);
  }

  
})();