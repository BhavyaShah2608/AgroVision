const dropContainer = document.getElementById('dropcontainer');
const fileInput = document.getElementsByClassName('drop-container-input')[0];
const fileUploadDiv = document.getElementsByClassName('drop-container-load')[0];
const resultsDiv = document.getElementById('drop-container-done-title');
const retryButton = document.getElementById('retry-upload-btn');
const fileUploadDivFill = document.getElementsByClassName(
	'drop-container-load-fill',
)[0];

function resetUploadSection() {
	fileInput.value = '';
	fileUploadDivFill.style.width = '0%';
	fileUploadDiv.style.display = 'none';
	dropContainer.style.display = 'flex';
	document.getElementById('drop-container-done').style.display = 'none';
	retryButton.style.display = 'none';
	dropContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
	setTimeout(() => fileInput.focus(), 300);
}

retryButton.addEventListener('click', resetUploadSection);

dropContainer.addEventListener(
	'dragover',
	(e) => {
		e.preventDefault();
	},
	false,
);

dropContainer.addEventListener('dragenter', () => {
	dropContainer.classList.add('drag-active');
});

dropContainer.addEventListener('dragleave', () => {
	dropContainer.classList.remove('drag-active');
});

dropContainer.addEventListener('drop', (e) => {
	e.preventDefault();
	dropContainer.classList.remove('drag-active');
	fileInput.files = e.dataTransfer.files;
});

// Replace 'your_cloud_name' with your Cloudinary cloud name
const cloudName = 'dk5acaaxg';
const uploadPreset = 'tzhnmdgj';

// Function to upload image to Cloudinary
function uploadImage(file) {
	const formData = new FormData();
	formData.append('file', file);
	formData.append('upload_preset', uploadPreset);
	fileUploadDiv.style.display = 'flex';
	//   return fetch(`https://api.cloudinary.com/v1_1/${cloudName}/image/upload`, {
	//     method: "POST",
	//     body: formData,
	//     folder: "TensionFlow_CodeCrafter",
	//   })
	//     .then((response) => response.json())
	//     .then((data) => {
	//       fileUploadDivFill.style.width = "100%";
	//       setTimeout(() => {
	//         fileUploadDiv.style.display = "none";
	//         document.getElementsByClassName(
	//           "drop-container-done"
	//         )[0].style.display = flex;
	//       }, 3000);
	//       return data.secure_url;
	//     })
	//     .catch((error) =>
	//       console.error("Error uploading image to Cloudinary:", error)
	//     );
	return fetch('https://bhavyashah2608-agrovision-backend.hf.space/upload', {
		method: 'POST',
		body: formData,
	})
		.then((response) => response.json())
		.then((result) => {
			let { disease } = result;
			let diseaseName = disease;
			diseaseName = diseaseName.replace(/_/g, ' ');
			const detailsUrl = `${window.location.origin}/predictions.html?disease=${disease}`;

			if (window.AgroVisionAuth) {
				window.AgroVisionAuth.ready().then(() => {
					window.AgroVisionAuth.saveLastSearch({
						disease,
						displayName: diseaseName,
						detailsUrl,
						percentage: result.percentage,
						predictionTime: result.time,
					});
				});
			}

			fileUploadDivFill.style.width = '100%';
			resultsDiv.querySelector('h2').innerText = `${diseaseName} is the disease that Your Plant is facing 😢`;
			resultsDiv.querySelector('a').setAttribute(
				'href',
				detailsUrl,
			);
			retryButton.style.display = 'inline-block';
			// <a href=${`${window.location.origin}/predictions?disease=${disease}`} >To Know About Causes, Effect and Treatments <i class="fa-solid fa-arrow-right"></i></a>`;

			setTimeout(() => {
				fileUploadDiv.style.display = 'none';
				dropContainer.style.display = 'none';
				document.getElementById('drop-container-done').style.display =
					'flex';
			}, 1000);

			console.log('Success:', result);
		})
		.catch((error) => {
			console.error('Error:', error);
			fileUploadDiv.style.display = 'none';
			fileUploadDivFill.style.width = '0%';
			alert('Image upload failed. Please try again.');
		});
}

fileInput.addEventListener('change', async (event) => {
	const file = event.target.files[0];
	const imageUrl = await uploadImage(file);
	// console.log('Image uploaded to Cloudinary:', imageUrl);
});
