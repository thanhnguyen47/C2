// DOM elements
const startBtn = document.getElementById('startBtn');
const attackBtn = document.getElementById('attackBtn');
const endSimulationBtn = document.getElementById('endSimulationBtn');
const attackConfigSection = document.getElementById('attackConfigSection');
const attackBtnContainer = document.getElementById('attackBtnContainer');
const alertContainer = document.getElementById('alertContainer');
const attackTypeSelect = document.getElementById('attackType');
const httpFloodOptions = document.getElementById('httpFloodOptions');
const synFloodOptions = document.getElementById('synFloodOptions');
const icmpFloodOptions = document.getElementById('icmpFloodOptions');
const spoofHeadersCheckbox = document.getElementById('spoofHeaders');
const customHeadersSection = document.getElementById('customHeadersSection');
const targetUrlInput = document.getElementById('targetUrl');
const botCountInput = document.getElementById('botCount');
const intensityInput = document.getElementById('intensity');
const durationInput = document.getElementById('duration');
const spoofHeadersInput = document.getElementById('spoofHeaders');
const customHeadersInput = document.getElementById('customHeaders');
const synTargetPortInput = document.getElementById('synTargetPort');
const synSpoofIpInput = document.getElementById('synSpoofIp');
const icmpTargetIpInput = document.getElementById('icmpTargetIp');
const icmpSpoofIpInput = document.getElementById('icmpSpoofIp');

// Display alert message
const showAlert = (message, type = "success") => {
    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
    alertContainer.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
};

// Toggle button spinner
const toggleSpinner = (button, show) => {
    const spinner = button.querySelector(".spinner-border");
    if (spinner) {
        button.disabled = show;
        spinner.classList.toggle("d-none", !show);
    }
};

// Toggle attack-specific options
const toggleAttackOptions = (attackType) => {
    httpFloodOptions.classList.toggle('d-none', attackType !== 'HTTP_FLOOD');
    synFloodOptions.classList.toggle('d-none', attackType !== 'SYN_FLOOD');
    icmpFloodOptions.classList.toggle('d-none', attackType !== 'ICMP_FLOOD');
};

// Display status message
const showMessage = (elementId, message, isError) => {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `mt-2 text-sm ${isError ? 'text-danger' : 'text-success'}`;
};

// Update UI based on attack state
const updateAttackUI = (isAttacking, attackDetails = null, targetUrl = null) => {
    if (targetUrl) {
        targetUrlInput.value = targetUrl;
        attackConfigSection.classList.remove('d-none');
        attackBtnContainer.classList.remove('d-none');
    } else {
        targetUrlInput.value = '';
        attackConfigSection.classList.add('d-none');
        attackBtnContainer.classList.add('d-none');
    }

    botCountInput.value = attackDetails?.bot_count || 1;

    if (isAttacking && attackDetails) {
        attackTypeSelect.value = attackDetails.attack_type || 'HTTP_FLOOD';
        toggleAttackOptions(attackDetails.attack_type);
        intensityInput.value = attackDetails.intensity || '';
        durationInput.value = attackDetails.duration || '';

        if (attackDetails.attack_type === 'HTTP_FLOOD') {
            spoofHeadersInput.checked = attackDetails.spoof_headers || false;
            customHeadersSection.classList.toggle('d-none', !attackDetails.spoof_headers);
            customHeadersInput.value = attackDetails.custom_headers ? JSON.stringify(attackDetails.custom_headers, null, 2) : '{}';
        } else if (attackDetails.attack_type === 'SYN_FLOOD') {
            synTargetPortInput.value = attackDetails.target_port || '';
            synSpoofIpInput.checked = attackDetails.spoof_ip || false;
        } else if (attackDetails.attack_type === 'ICMP_FLOOD') {
            icmpTargetIpInput.value = attackDetails.target_ip || '';
            icmpSpoofIpInput.checked = attackDetails.spoof_ip || false;
        }
    } else {
        attackTypeSelect.value = 'HTTP_FLOOD';
        toggleAttackOptions('HTTP_FLOOD');
        intensityInput.value = '';
        durationInput.value = '';
        spoofHeadersInput.checked = false;
        customHeadersSection.classList.add('d-none');
        customHeadersInput.value = '{}';
        synTargetPortInput.value = '';
        synSpoofIpInput.checked = false;
        icmpTargetIpInput.value = '';
        icmpSpoofIpInput.checked = false;
    }

    if (isAttacking && attackDetails) {
        attackBtn.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> Attacking...';
        attackBtn.disabled = true;
        attackBtn.classList.replace('btn-danger', 'btn-secondary');
    } else {
        attackBtn.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> Attack';
        attackBtn.disabled = false;
        attackBtn.classList.replace('btn-secondary', 'btn-danger');
    }
};

// Initialize attack state
const initializeAttackState = async () => {
    try {
        const response = await fetch('/ddos/get-status', { headers: { 'Content-Type': 'application/json' } });
        const result = await response.json();
        if (response.ok) {
            updateAttackUI(result.is_attacking, result.attack_details, result.target_url);
        } else {
            throw new Error(result.message || 'Failed to get attack status');
        }
    } catch (error) {
        showAlert(`Error loading attack status: ${error.message}`, "danger");
        updateAttackUI(false, null, null);
    }
};

// DOM event listeners
document.addEventListener("DOMContentLoaded", () => {
    // Toggle Custom Headers
    spoofHeadersCheckbox.addEventListener('change', () => {
        customHeadersSection.classList.toggle('d-none', !spoofHeadersCheckbox.checked);
    });

    // Toggle Attack Type
    attackTypeSelect.addEventListener('change', () => toggleAttackOptions(attackTypeSelect.value));

    // Start Button
    startBtn.addEventListener('click', async (event) => {
        event.preventDefault();
        toggleSpinner(startBtn, true);
        startBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';

        try {
            const response = await fetch('/ddos/start-target', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `bot_count=${botCountInput.value || 1}`
            });
            const result = await response.json();
            if (response.ok) {
                targetUrlInput.value = result.target;
                attackConfigSection.classList.remove('d-none');
                attackBtnContainer.classList.remove('d-none');
                startBtn.innerHTML = '<i class="bi bi-play-fill"></i> Started';
                startBtn.classList.replace('btn-primary', 'btn-success');
                showMessage('startTargetMessage', `Target started: ${result.target}`, false);
                showAlert(`Target started: ${result.target}`, "success");
                await initializeAttackState();
            } else {
                throw new Error(result.message || 'Failed to start target');
            }
        } catch (error) {
            showMessage('startTargetMessage', `Error starting target: ${error.message}`, true);
            showAlert(`Error starting target: ${error.message}`, "danger");
            startBtn.innerHTML = '<i class="bi bi-play-fill"></i> Start';
            startBtn.classList.replace('btn-success', 'btn-primary');
        } finally {
            toggleSpinner(startBtn, false);
        }
    });

    // Attack Button
    attackBtn.addEventListener('click', async () => {
        try {
            const statusResponse = await fetch('/ddos/get-status', { headers: { 'Content-Type': 'application/json' } });
            const statusResult = await statusResponse.json();
            if (!statusResponse.ok) {
                throw new Error(statusResult.message || 'Failed to get attack status');
            }
            const isAttacking = statusResult.is_attacking;

            if (!isAttacking) {
                const intensity = parseInt(intensityInput.value);
                const attackType = attackTypeSelect.value;
                const duration = parseInt(durationInput.value);
                const targetUrl = targetUrlInput.value;

                if (!intensity || !attackType || !duration || !targetUrl) {
                    showAlert('Please fill in all required fields.', "danger");
                    return;
                }
                if (isNaN(intensity) || intensity <= 0) {
                    showAlert('Intensity must be a positive number.', "danger");
                    return;
                }
                if (isNaN(duration) || duration <= 0) {
                    showAlert('Duration must be a positive number.', "danger");
                    return;
                }

                const attackConfig = {
                    attack_type: attackType,
                    intensity,
                    duration,
                    target_url: targetUrl,
                    spoof_headers: false,
                    custom_headers: {},
                    target_port: null,
                    spoof_ip: false,
                    target_ip: null
                };

                if (attackType === 'HTTP_FLOOD') {
                    attackConfig.spoof_headers = spoofHeadersInput.checked;
                    if (attackConfig.spoof_headers) {
                        try {
                            attackConfig.custom_headers = JSON.parse(customHeadersInput.value || '{}');
                            if (typeof attackConfig.custom_headers !== 'object' || Array.isArray(attackConfig.custom_headers)) {
                                throw new Error('Custom headers must be a valid JSON object.');
                            }
                        } catch (error) {
                            showAlert(`Invalid custom headers JSON: ${error.message}`, "danger");
                            return;
                        }
                    }
                } else if (attackType === 'SYN_FLOOD') {
                    const synTargetPort = parseInt(synTargetPortInput.value);
                    if (isNaN(synTargetPort) || synTargetPort <= 0 || synTargetPort > 65535) {
                        showAlert('Target Port for SYN Flood must be between 1 and 65535.', "danger");
                        return;
                    }
                    attackConfig.target_port = synTargetPort;
                    attackConfig.spoof_ip = synSpoofIpInput.checked;
                } else if (attackType === 'ICMP_FLOOD') {
                    const icmpTargetIp = icmpTargetIpInput.value;
                    if (!icmpTargetIp || !/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(icmpTargetIp)) {
                        showAlert('Please enter a valid Target IP for ICMP Flood.', "danger");
                        return;
                    }
                    attackConfig.target_ip = icmpTargetIp;
                    attackConfig.spoof_ip = icmpSpoofIpInput.checked;
                }

                toggleSpinner(attackBtn, true);
                attackBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Attacking...';

                const response = await fetch('/ddos/attack-target', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(attackConfig)
                });
                const result = await response.json();

                if (response.ok && result.status === 'started') {
                    updateAttackUI(true, {
                        attack_id: result.attack_id,
                        target_url: targetUrl,
                        attack_type: attackType,
                        intensity,
                        duration,
                        spoof_headers: attackConfig.spoof_headers,
                        custom_headers: attackConfig.custom_headers,
                        spoof_ip: attackConfig.spoof_ip,
                        target_port: attackConfig.target_port,
                        target_ip: attackConfig.target_ip,
                        bot_count: statusResult.attack_details?.bot_count || botCountInput.value
                    }, targetUrl);
                    showAlert(`Attack started on ${targetUrl}`, "success");
                } else {
                    throw new Error(result.detail || result.message || 'Failed to launch attack');
                }
            } else {
                showAlert('Attack is already in progress.', "warning");
            }
        } catch (error) {
            showAlert(`Error: ${error.message}`, "danger");
        } finally {
            toggleSpinner(attackBtn, false);
        }
    });

    // End Simulation Button
    endSimulationBtn.addEventListener('click', async (event) => {
        event.preventDefault();
        toggleSpinner(endSimulationBtn, true);
        endSimulationBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Stopping...';

        try {
            const response = await fetch('/ddos/stop-target', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const result = await response.json();
            if (response.ok) {
                attackConfigSection.classList.add('d-none');
                attackBtnContainer.classList.add('d-none');
                startBtn.innerHTML = '<i class="bi bi-play-fill"></i> Start';
                startBtn.disabled = false;
                startBtn.classList.replace('btn-success', 'btn-primary');
                updateAttackUI(false, null, null);
                showMessage('startTargetMessage', '', false);
                showAlert('Simulation stopped.', "success");
            } else {
                throw new Error(result.message || 'Failed to stop simulation');
            }
        } catch (error) {
            showAlert(`Error stopping simulation: ${error.message}`, "danger");
            endSimulationBtn.innerHTML = '<i class="bi bi-stop-fill"></i> End Simulation';
        } finally {
            toggleSpinner(endSimulationBtn, false);
        }
    });

    // Initialize
    toggleAttackOptions('HTTP_FLOOD');
    initializeAttackState();
});