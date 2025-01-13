document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('downloadForm');
  form.addEventListener('submit', (event) => {
    event.preventDefault();

    const videoUrl = document.getElementById("videoUrl").value;
    const statusDiv = document.getElementById("status");
    const loader = document.getElementById("loader");

    statusDiv.textContent = "Downloading...";
    statusDiv.className = ""; // Reset class
    loader.style.display = "block"; // Show loader

    fetch("/enqueue_download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: videoUrl,
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
        statusDiv.textContent = data.message || "Download request received";
        statusDiv.className = data.success ? "success" : "error";
      })
      .catch((error) => {
        loader.style.display = "none"; // Hide loader
        console.error("Full error:", error);
        statusDiv.textContent = error.message || "Download failed";
        statusDiv.className = "error";
      });
  });
});
