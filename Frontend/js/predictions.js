let predictionImg = document.getElementById('prediction-image');
let predictionName = document.getElementById('prediction-name');
let predictionDesc = document.getElementById('prediction-desc');
let lastSearchName = document.getElementById('last-search-name');
let lastSearchMeta = document.getElementById('last-search-meta');
let lastSearchLink = document.getElementById('last-search-link');

function renderHistoryRecord(record) {
	if (!record) {
		if (lastSearchName) {
			lastSearchName.textContent = 'No saved disease yet.';
		}
		if (lastSearchMeta) {
			lastSearchMeta.textContent = 'Sign in and run a prediction to keep your latest disease here.';
		}
		if (lastSearchLink) {
			lastSearchLink.hidden = true;
		}
		return;
	}

	if (lastSearchName) {
		lastSearchName.textContent = record.displayName || record.disease;
	}
	if (lastSearchMeta) {
		lastSearchMeta.textContent = record.timestamp ? `Saved ${new Date(record.timestamp).toLocaleString()}` : 'Saved disease prediction.';
	}
	if (lastSearchLink) {
		lastSearchLink.hidden = !record.detailsUrl;
		lastSearchLink.href = record.detailsUrl || '#';
	}
}

window.addEventListener('DOMContentLoaded', () => {
	const url = new URL(window.location.href);
	const params = new URLSearchParams(url.search);
	const disease = params.get('disease');
	let formData = new FormData();
	formData.append('disease', disease);

	if (window.AgroVisionAuth) {
		window.AgroVisionAuth.ready().then(() => {
			const currentUser = window.AgroVisionAuth.getCurrentUser();
			renderHistoryRecord(currentUser ? window.AgroVisionAuth.getLastSearch(currentUser.uid) : null);
		});
	}

	return fetch('http://localhost:5001/diseasedetail', {
		method: 'POST',
		body: formData,
	})
		.then((response) => response.json())
		.then((result) => {
			let { link, name, description } = result;
			predictionImg.style.backgroundImage = `url(${link})`;
			predictionName.innerHTML = name;
			predictionDesc.innerHTML = description.map((desc) => `<li>${desc}</li>`).join('');

			if (window.AgroVisionAuth) {
				window.AgroVisionAuth.ready().then(() => {
					const currentUser = window.AgroVisionAuth.getCurrentUser();
					if (currentUser) {
						window.AgroVisionAuth.saveLastSearch({
							disease,
							displayName: name,
							detailsUrl: window.location.href,
							timestamp: new Date().toISOString(),
						});
						renderHistoryRecord(window.AgroVisionAuth.getLastSearch(currentUser.uid));
					} else {
						renderHistoryRecord(null);
					}
				});
			}
		});
});
