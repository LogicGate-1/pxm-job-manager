// static/scripts.js
document.addEventListener('DOMContentLoaded', () => {
    const checkboxes = document.querySelectorAll('.job-checkbox');
    const selectAll = document.getElementById('select-all');
    const loadBtn = document.getElementById('load-pxm-btn');
    const driveSelect = document.getElementById('pxm-drive');
    const dataDiv = document.getElementById('dashboard-data');

    const updateButton = () => {
        const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
        loadBtn.style.display = anyChecked ? 'inline-block' : 'none';
    };

    checkboxes.forEach(cb => cb.addEventListener('change', updateButton));

    if (selectAll) {
        selectAll.addEventListener('change', () => {
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
            updateButton();
        });
    }

    loadBtn.addEventListener('click', () => {
        const selected = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.nextElementSibling.textContent.trim());

        if (!selected.length) return;
        if (!driveSelect.value) {
            alert("Please select PXM Drive first");
            return;
        }

        const formData = new FormData();
        selected.forEach(job => formData.append('selected_jobs', job));
        formData.append('dh', dataDiv.dataset.dh);
        formData.append('type', dataDiv.dataset.type);
        formData.append('drive_letter', driveSelect.value);

        fetch('/load-to-pxm', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(message => {
            alert(message);
            // Clear selections
            checkboxes.forEach(cb => cb.checked = false);
            selectAll.checked = false;
            updateButton();
        })
        .catch(err => alert("Error: " + err.message));
    });
});