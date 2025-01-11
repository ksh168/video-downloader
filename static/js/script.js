document.addEventListener('DOMContentLoaded', () => {
  const socket = io();
  const clientId = Math.random().toString(36).substring(7);

  socket.on('connect', () => {
    socket.emit('register_client', { clientId });
  });

  socket.on('download_progress', (data) => {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = `Download Progress: ${data.progress.toFixed(1)}%`;
  });

  const form = document.getElementById('downloadForm');
  form.addEventListener('submit', (event) => {
    event.preventDefault();

    const videoUrl = document.getElementById("videoUrl").value;
    const statusDiv = document.getElementById("status");
    const loader = document.getElementById("loader");

    statusDiv.textContent = "Downloading...";
    statusDiv.className = ""; // Reset class
    loader.style.display = "block"; // Show loader

    fetch("/download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: videoUrl,
        client_id: clientId
      }),
    })
      .then((response) => {
        loader.style.display = "none"; // Hide loader
        if (!response.ok) {
          return response.json().then((err) => {
            console.error("Detailed error:", err);
            throw new Error(err.error || "Download failed");
          });
        }
        return response.json();
      })
      .then((data) => {
        if (data.success) {
          const downloadButton = document.createElement("a");
          downloadButton.href = data.download_url;
          downloadButton.textContent = "Click here to download";
          downloadButton.className = "download-button";

          statusDiv.innerHTML = ""; // Clear previous status
          statusDiv.appendChild(downloadButton);
        } else {
          statusDiv.textContent = data.message || "Download failed";
        }
        statusDiv.className = "";
      })
      .catch((error) => {
        loader.style.display = "none"; // Hide loader
        console.error("Full error:", error);
        statusDiv.textContent = error.message || "Download failed";
        statusDiv.className = "error";
      });
  });
});
