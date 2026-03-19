(function () {
  const loaderMessage = document.getElementById("loaderMessage");
  const jsonUrl = document.getElementById("jsonUrl");
  const loadFromUrlBtn = document.getElementById("loadFromUrlBtn");
  const jsonFileInput = document.getElementById("jsonFileInput");

  function setMessage(text, isError) {
    loaderMessage.textContent = text;
    loaderMessage.className = isError ? "mt-4 text-sm text-red-600 font-medium" : "mt-4 text-sm text-slate-600";
  }

  function goToAnalysis(payload) {
    try {
      sessionStorage.setItem("atlas_report", JSON.stringify(payload));
      window.location.href = "analysis.html";
    } catch (e) {
      setMessage("Αποτυχία αποθήκευσης δεδομένων: " + e.message, true);
    }
  }

  loadFromUrlBtn.addEventListener("click", async function () {
    const url = (jsonUrl.value || "").trim();
    if (!url) {
      setMessage("Δώστε URL JSON.", true);
      return;
    }
    try {
      setMessage("Φόρτωση...");
      const resp = await fetch(url);
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const json = await resp.json();
      goToAnalysis(json);
    } catch (err) {
      setMessage("Αποτυχία: " + err.message, true);
    }
  });

  jsonFileInput.addEventListener("change", async function (evt) {
    const file = evt.target.files && evt.target.files[0];
    if (!file) return;
    try {
      setMessage("Ανάγνωση αρχείου...");
      const text = await file.text();
      const json = JSON.parse(text);
      goToAnalysis(json);
    } catch (err) {
      setMessage("Μη έγκυρο JSON: " + err.message, true);
    }
  });
})();
