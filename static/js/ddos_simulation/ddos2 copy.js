const startBtn = document.getElementById('startBtn');
const attackBtn = document.getElementById('attackBtn');
const endSimulationBtn = document.getElementById('endSimulationBtn');
const refreshChartBtn = document.getElementById('refreshChartBtn');
const exportPcapBtn = document.getElementById('exportPcapBtn');
const attackConfigSection = document.getElementById('attackConfigSection');
const attackBtnContainer = document.getElementById('attackBtnContainer');
const alertContainer = document.getElementById('alertContainer');
const attackTypeSelect = document.getElementById('attackType');
const httpFloodOptions = document.getElementById('httpFloodOptions');
const synFloodOptions = document.getElementById('synFloodOptions');
const udpFloodOptions = document.getElementById('udpFloodOptions');
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
const udpTargetPortInput = document.getElementById('udpTargetPort');
const packetSizeInput = document.getElementById('packetSize');
const udpSpoofIpInput = document.getElementById('udpSpoofIp');

// Hàm hiển thị thông báo
const showAlert = (message, type = "success") => {
    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
    alertContainer.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
};

// Hàm bật/tắt spinner
const toggleSpinner = (button, show) => {
    const spinner = button.querySelector(".spinner-border");
    if (spinner) {
        button.disabled = show;
        spinner.classList.toggle("d-none", !show);
    }
};

// Hàm toggle options dựa trên attack type
const toggleAttackOptions = (attackType) => {
    httpFloodOptions.classList.toggle('d-none', attackType !== 'HTTP_FLOOD');
    synFloodOptions.classList.toggle('d-none', attackType !== 'SYN_FLOOD');
    udpFloodOptions.classList.toggle('d-none', attackType !== 'UDP_FLOOD');
};

// Hàm hiển thị thông báo trạng thái
const showMessage = (elementId, message, isError) => {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `mt-2 text-sm ${isError ? 'text-danger' : 'text-success'}`;
};

// Hàm cập nhật UI dựa trên trạng thái tấn công
const updateAttackUI = (isAttacking, attackDetails = null, targetUrl = null) => {
    // Cập nhật target URL và các section
    if (targetUrl) {
        targetUrlInput.value = targetUrl;
        attackConfigSection.classList.remove('d-none');
        attackBtnContainer.classList.remove('d-none');
    } else {
        targetUrlInput.value = '';
        attackConfigSection.classList.add('d-none');
        attackBtnContainer.classList.add('d-none');
    }

    // Cập nhật bot count
    botCountInput.value = attackDetails?.bot_count || 1;

    // Cập nhật configuration inputs
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
        } else if (attackDetails.attack_type === 'UDP_FLOOD') {
            udpTargetPortInput.value = attackDetails.target_port || '';
            packetSizeInput.value = attackDetails.packet_size || '';
            udpSpoofIpInput.checked = attackDetails.spoof_ip || false;
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
        udpTargetPortInput.value = '';
        packetSizeInput.value = '';
        udpSpoofIpInput.checked = false;
    }

    // Cập nhật trạng thái tấn công
    if (isAttacking && attackDetails) {
        // attackBtn.innerHTML = '<i class="bi bi-pause-fill"></i> Stop';
        attackBtn.innerHTML='<i class="bi bi-exclamation-triangle-fill"></i> Attackin...'
        attackBtn.disabled=true
        attackBtn.classList.replace('btn-danger', 'btn-secondary');
    } else {
        attackBtn.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> Attack';
        attackBtn.classList.replace('btn-secondary', 'btn-danger');
    }
};

// Hàm khởi tạo trạng thái tấn công
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

// Sự kiện DOM
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
                    packet_size: null
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
                } else if (attackType === 'UDP_FLOOD') {
                    const udpTargetPort = parseInt(udpTargetPortInput.value);
                    const packetSize = parseInt(packetSizeInput.value);
                    if (isNaN(udpTargetPort) || udpTargetPort <= 0 || udpTargetPort > 65535) {
                        showAlert('Target Port for UDP Flood must be between 1 and 65535.', "danger");
                        return;
                    }
                    if (isNaN(packetSize) || packetSize <= 0) {
                        showAlert('Packet Size for UDP Flood must be a positive number.', "danger");
                        return;
                    }
                    attackConfig.target_port = udpTargetPort;
                    attackConfig.packet_size = packetSize;
                    attackConfig.spoof_ip = udpSpoofIpInput.checked;
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
                        packet_size: attackConfig.packet_size,
                        target_port: attackConfig.target_port,
                        bot_count: statusResult.attack_details?.bot_count || botCountInput.value
                    }, targetUrl);
                    showAlert(`Attack started on ${targetUrl}`, "success");
                } else {
                    throw new Error(result.detail || result.message || 'Failed to launch attack');
                }
            }
        } catch (error) {
            showAlert(`Error: ${error.message}`, "danger");
        } finally {
            toggleSpinner(attackBtn, false);
            attackBtn.innerHTML = isAttacking ? '<i class="bi bi-pause-fill"></i> Stop' : '<i class="bi bi-exclamation-triangle-fill"></i> Attack';
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
    // Khởi tạo
    toggleAttackOptions('HTTP_FLOOD');
    initializeAttackState();
});