
const startBtn = document.getElementById('startBtn');
const targetDomainDisplay = document.getElementById('targetDomainDisplay');
const targetDomainText = document.getElementById('targetDomainText');
const attackConfigSection = document.getElementById('attackConfigSection');
const attackBtnContainer = document.getElementById('attackBtnContainer');
const attackBtn = document.getElementById('attackBtn');
const endSimulationBtn = document.getElementById('endSimulationBtn');

// Xử lý khi nhấn nút Start
startBtn.addEventListener('click', function (event) {
    event.preventDefault()
    startBtn.textContent = 'Starting...';
    startBtn.disabled = true;

    fetch("/ddos/start-target", {
        method: "POST"
    })
    .then(r=>r.json())
    .then(j=>{
        targetDomainText.textContent = j.target

        targetDomainDisplay.classList.remove('d-none');
        attackConfigSection.classList.remove('d-none');
        attackBtnContainer.classList.remove('d-none');

        startBtn.textContent = 'Started';
        startBtn.classList.remove('btn-primary');
        startBtn.classList.add('btn-success');
    })
    .catch(e=>console.error(e))
});

// Xử lý khi nhấn nút Attack
attackBtn.addEventListener('click', function (event) {
    event.preventDefault()
    if (attackBtn.textContent === 'Attack') {
        const numRequests = document.getElementById('numRequests').value;
        const attackType = document.getElementById('attackType').value;
        const duration = document.getElementById('duration').value;
        const botCount = document.getElementById('botCount').value;

        // Kiểm tra nếu các trường cấu hình chưa được điền
        if (!numRequests || !attackType || !duration || !botCount) {
            alert('Please fill in all configuration fields before attacking.');
            return;
        }

        // Giả lập bắt đầu tấn công
        alert(`Attack started on ${targetDomainText.textContent} with ${numRequests} requests, type: ${attackType}, duration: ${duration} minutes, using ${botCount} bots.`);

        // Chuyển nút Attack thành Stop
        attackBtn.textContent = 'Stop';
        attackBtn.classList.remove('btn-danger');
        attackBtn.classList.add('btn-secondary');
    } else {
        // Giả lập dừng tấn công
        alert('Attack stopped.');

        // Chuyển nút Stop thành Attack
        attackBtn.textContent = 'Attack';
        attackBtn.classList.remove('btn-secondary');
        attackBtn.classList.add('btn-danger');
    }
});

// Xử lý khi nhấn nút End Simulation
endSimulationBtn.addEventListener('click', function (event) {
    event.preventDefault()
    fetch("/ddos/stop-target", {
        method: "POST"
    })
    .then(r=>{
        if (r.ok) {
            // Ẩn tất cả các phần liên quan
            targetDomainDisplay.classList.add('d-none');
            attackConfigSection.classList.add('d-none');
            attackBtnContainer.classList.add('d-none');

            // Đặt lại trạng thái nút Start
            startBtn.textContent = 'Start';
            startBtn.disabled = false;
            startBtn.classList.remove('btn-success');
            startBtn.classList.add('btn-primary');
        } else {
            alert("stop fail")
        }
    })
});