const startBtn = document.getElementById('startBtn');
const attackConfigSection = document.getElementById('attackConfigSection');
const attackDetailsSection = document.getElementById('attackDetailsSection')
const attackMonitoringSection = document.getElementById('attackMonitoringSection')
const attackBtnContainer = document.getElementById('attackBtnContainer');
const attackBtn = document.getElementById('attackBtn');
const endSimulationBtn = document.getElementById('endSimulationBtn');

// Toggle Attack Type Options
const attackTypeSelect = document.getElementById('attackType');
const httpFloodOptions = document.getElementById('httpFloodOptions');
const synFloodOptions = document.getElementById('synFloodOptions');
const udpFloodOptions = document.getElementById('udpFloodOptions');
const spoofHeadersCheckbox = document.getElementById('spoofHeaders');
const customHeadersSection = document.getElementById('customHeadersSection');

function toggleAttackOptions() {
    const attackType = attackTypeSelect.value;
    httpFloodOptions.classList.add('d-none');
    synFloodOptions.classList.add('d-none');
    udpFloodOptions.classList.add('d-none');

    if (attackType === 'HTTP_FLOOD') {
        httpFloodOptions.classList.remove('d-none');
    } else if (attackType === 'SYN_FLOOD') {
        synFloodOptions.classList.remove('d-none');
    } else if (attackType === 'UDP_FLOOD') {
        udpFloodOptions.classList.remove('d-none');
    }
}

attackTypeSelect.addEventListener('change', toggleAttackOptions);

// Toggle Custom Headers
spoofHeadersCheckbox.addEventListener('change', function () {
    customHeadersSection.classList.toggle('d-none', !spoofHeadersCheckbox.checked);
});

// Helper to display messages
function showMessage(elementId, message, isError) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `mt-2 text-sm ${isError ? 'text-danger' : 'text-success'}`;
}

// Xử lý khi nhấn nút Start
startBtn.addEventListener('click', function (event) {
    event.preventDefault();
    startBtn.textContent = 'Starting...';
    startBtn.disabled = true;

    const botCount = document.getElementById('botCount').value;

    fetch('/ddos/start-target', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `bot_count=${botCount}`
    })
    .then(r => r.json())
    .then(j => {
        document.getElementById('targetUrl').value = j.target;
        attackConfigSection.classList.remove('d-none');
        attackBtnContainer.classList.remove('d-none');

        startBtn.textContent = 'Started';
        startBtn.classList.remove('btn-primary');
        startBtn.classList.add('btn-success');

        showMessage('startTargetMessage', `Target started: ${j.target}`);
    })
    .catch(e => {
        showMessage('startTargetMessage', 'Error starting target: ' + e.message, true);
        startBtn.textContent = 'Start';
        startBtn.disabled = false;
        startBtn.classList.remove('btn-success');
        startBtn.classList.add('btn-primary');
        console.error(e);
    });
});

// Xử lý khi nhấn nút Attack
attackBtn.addEventListener('click', async function () {
    if (attackBtn.textContent === 'Attack') {
        // Lấy dữ liệu từ các input
        const intensity = parseInt(document.getElementById('intensity').value);
        const attackType = document.getElementById('attackType').value;
        const duration = parseInt(document.getElementById('duration').value);
        const targetUrl = document.getElementById('targetUrl').value;

        // Kiểm tra nếu các trường bắt buộc chưa được điền
        if (!intensity || !attackType || !duration || !targetUrl) {
            alert('Please fill in all required configuration fields (Intensity, Attack Type, Duration, Target URL).');
            return;
        }

        // Kiểm tra giá trị hợp lệ
        if (isNaN(intensity) || intensity <= 0) {
            alert('Intensity must be a positive number.');
            return;
        }
        if (isNaN(duration) || duration <= 0) {
            alert('Duration must be a positive number.');
            return;
        }

        // HTTP Flood Options
        const spoofHeaders = document.getElementById('spoofHeaders')?.checked || false;
        let customHeaders = {};
        if (spoofHeaders) {
            try {
                const customHeadersInput = document.getElementById('customHeaders').value || '{}';
                customHeaders = JSON.parse(customHeadersInput);
                if (typeof customHeaders !== 'object' || Array.isArray(customHeaders)) {
                    throw new Error('Custom headers must be a valid JSON object.');
                }
            } catch (error) {
                alert('Invalid custom headers JSON: ' + error.message);
                return;
            }
        }

        // SYN Flood Options
        const synTargetPort = document.getElementById('synTargetPort') ? parseInt(document.getElementById('synTargetPort').value) : null;
        const synSpoofIp = document.getElementById('synSpoofIp')?.checked || false;

        // UDP Flood Options
        const udpTargetPort = document.getElementById('udpTargetPort') ? parseInt(document.getElementById('udpTargetPort').value) : null;
        const packetSize = document.getElementById('packetSize') ? parseInt(document.getElementById('packetSize').value) : null;
        const udpSpoofIp = document.getElementById('udpSpoofIp')?.checked || false;

        // Kiểm tra giá trị hợp lệ cho target_port và packet_size
        if (attackType === 'SYN_FLOOD' && (isNaN(synTargetPort) || synTargetPort <= 0 || synTargetPort > 65535)) {
            alert('Target Port for SYN Flood must be a number between 1 and 65535.');
            return;
        }
        if (attackType === 'UDP_FLOOD') {
            if (isNaN(udpTargetPort) || udpTargetPort <= 0 || udpTargetPort > 65535) {
                alert('Target Port for UDP Flood must be a number between 1 and 65535.');
                return;
            }
            if (isNaN(packetSize) || packetSize <= 0) {
                alert('Packet Size for UDP Flood must be a positive number.');
                return;
            }
        }

        // Tạo đối tượng attackConfig khớp với AttackRequest
        const attackConfig = {
            attack_type: attackType,
            intensity: intensity,
            duration: duration,
            target_url: targetUrl,
            spoof_headers: spoofHeaders,
            custom_headers: customHeaders,
            target_port: null,
            spoof_ip: false,
            packet_size: null
        };

        // Gán các giá trị tùy chọn theo loại tấn công
        if (attackType === 'HTTP_FLOOD') {
            attackConfig.spoof_headers = spoofHeaders;
            attackConfig.custom_headers = customHeaders;
        } else if (attackType === 'SYN_FLOOD') {
            attackConfig.target_port = synTargetPort;
            attackConfig.spoof_ip = synSpoofIp;
        } else if (attackType === 'UDP_FLOOD') {
            attackConfig.target_port = udpTargetPort;
            attackConfig.packet_size = packetSize;
            attackConfig.spoof_ip = udpSpoofIp;
        }

        try {
            // Gửi request tới endpoint /ddos/attack-target
            const response = await fetch('/ddos/attack-target', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(attackConfig)
            });

            // Kiểm tra phản hồi từ server
            const result = await response.json();
            if (response.ok && result.status === 'started') {
                // Hiển thị thông tin tấn công trong attackDetailsSection
                attackDetails.innerHTML = `
                    <ul class="list-group">
                        <li class="list-group-item"><strong>Attack ID:</strong> ${result.attack_id}</li>
                        <li class="list-group-item"><strong>Target URL:</strong> ${targetUrl}</li>
                        <li class="list-group-item"><strong>Attack Type:</strong> ${attackType}</li>
                        <li class="list-group-item"><strong>Intensity (RPS):</strong> ${intensity}</li>
                        <li class="list-group-item"><strong>Duration:</strong> ${duration} seconds</li>
                    </ul>
                `;

                // Hiển thị các section
                attackDetailsSection.classList.remove('d-none');
                attackMonitoringSection.classList.remove('d-none');

                // Cập nhật nút Attack thành Stop
                attackBtn.textContent = 'Stop';
                attackBtn.classList.remove('btn-danger');
                attackBtn.classList.add('btn-secondary');

                alert(`Attack started on ${targetUrl} with ${intensity} requests per bot, type: ${attackType}, duration: ${duration} seconds.`);
            } else {
                // Xử lý lỗi từ server
                throw new Error(result.detail || result.message || 'Failed to launch attack');
            }
        } catch (error) {
            alert('Error launching attack: ' + error.message);
            console.error(error);
        }
    } else {
        // Xử lý khi nhấn Stop
        try {
            const response = await fetch('/ddos/stop-target', {
                method: 'POST'
            });
            const result = await response.json();

            if (response.ok && result.message === 'target stopped and removed') {
                alert('Attack stopped.');

                // Ẩn các section
                attackDetailsSection.classList.add('d-none');
                attackMonitoringSection.classList.add('d-none');

                // Cập nhật nút Stop thành Attack
                attackBtn.textContent = 'Attack';
                attackBtn.classList.remove('btn-secondary');
                attackBtn.classList.add('btn-danger');
            } else {
                throw new Error(result.message || 'Failed to stop attack');
            }
        } catch (error) {
            alert('Error stopping attack: ' + error.message);
            console.error(error);
        }
    }
});

// Xử lý khi nhấn nút End Simulation
endSimulationBtn.addEventListener('click', function (event) {
    event.preventDefault();
    fetch('/ddos/stop-target', {
        method: 'POST'
    })
    .then(r => {
        if (r.ok) {
            return r.json();
        } else {
            throw new Error('Failed to stop simulation');
        }
    })
    .then(j => {
        attackConfigSection.classList.add('d-none');
        attackBtnContainer.classList.add('d-none');

        startBtn.textContent = 'Start';
        startBtn.disabled = false;
        startBtn.classList.remove('btn-success');
        startBtn.classList.add('btn-primary');

        attackBtn.textContent = 'Attack';
        attackBtn.classList.remove('btn-secondary');
        attackBtn.classList.add('btn-danger');

        showMessage('startTargetMessage', '');
    })
    .catch(e => {
        alert('Error stopping simulation: ' + e.message);
        console.error(e);
    });
});

// Initialize attack options on load
toggleAttackOptions();