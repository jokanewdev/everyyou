document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingBox = document.getElementById('loadingBox');
    const errorBox = document.getElementById('errorBox');
    const previewCard = document.getElementById('previewCard');
    const progressCard = document.getElementById('progressCard');
    
    // Auto-analisar ao colar a URL (Experiência Inteligente)
    urlInput.addEventListener('paste', () => {
        setTimeout(() => { if (urlInput.value) analyzeMedia(); }, 100);
    });

    analyzeBtn.addEventListener('click', analyzeMedia);

    async function analyzeMedia() {
        const url = urlInput.value.trim();
        if (!url) return showError("Por favor, insira um link válido.");

        // UI Reset
        errorBox.classList.add('d-none');
        previewCard.classList.add('d-none');
        progressCard.classList.add('d-none');
        loadingBox.classList.remove('d-none');
        analyzeBtn.disabled = true;

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Erro ao analisar o link");

            renderPreview(data, url);
        } catch (error) {
            showError(error.message);
        } finally {
            loadingBox.classList.add('d-none');
            analyzeBtn.disabled = false;
        }
    }

    function renderPreview(data, originalUrl) {
        document.getElementById('mediaThumbnail').src = data.thumbnail;
        document.getElementById('mediaTitle').textContent = data.title;
        document.getElementById('mediaDuration').textContent = data.duration;
        document.getElementById('mediaPlatform').textContent = data.platform;

        const select = document.getElementById('formatSelect');
        select.innerHTML = '';
        
        data.formats.forEach(f => {
            const option = document.createElement('option');
            option.value = f.format_id;
            // Se for áudio, adiciona um ícone visual (emocore)
            option.textContent = f.type === 'audio' ? `🎵 ${f.quality}` : `🎥 ${f.quality}`;
            select.appendChild(option);
        });

        previewCard.classList.remove('d-none');

        // Configura o botão de download com a URL atual
        const dlBtn = document.getElementById('downloadBtn');
        dlBtn.onclick = () => startDownload(originalUrl, select.value);
    }

    async function startDownload(url, format_id) {
        document.getElementById('downloadBtn').disabled = true;
        progressCard.classList.remove('d-none');
        document.getElementById('progressStatus').textContent = "Iniciando...";
        
        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, format_id })
            });
            const data = await response.json();
            pollProgress(data.task_id);
        } catch (error) {
            showError("Falha ao iniciar o download.");
            document.getElementById('downloadBtn').disabled = false;
        }
    }

    function pollProgress(taskId) {
        const bar = document.getElementById('progressBar');
        const status = document.getElementById('progressStatus');
        const speed = document.getElementById('progressSpeed');
        const eta = document.getElementById('progressEta');

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${taskId}`);
                const data = await res.json();

                if (data.status === 'downloading') {
                    status.textContent = `Baixando... ${data.percent}%`;
                    bar.style.width = `${data.percent}%`;
                    speed.textContent = data.speed;
                    eta.textContent = data.eta;
                } else if (data.status === 'processing') {
                    status.textContent = "Processando arquivo (Mesclando Áudio/Vídeo)...";
                    bar.classList.add('progress-bar-animated');
                } else if (data.status === 'completed') {
                    clearInterval(interval);
                    status.textContent = "Download Concluído!";
                    bar.style.width = "100%";
                    bar.classList.remove('progress-bar-animated');
                    bar.classList.add('bg-success');
                    
                    // Dispara o download nativo do navegador
                    window.location.href = `/api/file/${taskId}`;
                    document.getElementById('downloadBtn').disabled = false;
                } else if (data.status === 'error') {
                    clearInterval(interval);
                    showError("Erro no processamento: " + data.error_msg);
                    progressCard.classList.add('d-none');
                    document.getElementById('downloadBtn').disabled = false;
                }
            } catch (e) {
                console.error("Erro na comunicação com servidor");
            }
        }, 1000);
    }

    function showError(msg) {
        errorBox.textContent = msg;
        errorBox.classList.remove('d-none');
    }
});