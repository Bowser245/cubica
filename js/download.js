document.addEventListener("DOMContentLoaded", () => {
    // Chemin vers le fichier JSON des versions
    const jsonUrl = "versions.json";

    // Sélection des éléments HTML à modifier dynamiquement
    const versionTitle = document.getElementById("version-title");
    const downloadBtn = document.getElementById("download-btn");

    // Récupération des données du JSON
    fetch(jsonUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error("Impossible de charger le fichier des versions");
            }
            return response.json();
        })
        .then(data => {
            // Mise à jour du titre avec la version (ex: Client de Jeu Principal (Cubica v1.0))
            if (versionTitle) {
                versionTitle.textContent = `Client de Jeu Principal (Cubica ${data.version})`;
            }
            // Mise à jour de l'attribut href du bouton de téléchargement
            if (downloadBtn) {
                downloadBtn.href = data.url;
            }
        })
        .catch(error => {
            // Debug sans caractères spéciaux dans la console
            console.error("Erreur de recuperation de la version:", error);
        });
});
