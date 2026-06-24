const firebaseConfig = window.__FIREBASE_CONFIG__ || {
	apiKey: 'REPLACE_WITH_FIREBASE_WEB_API_KEY',
	authDomain: 'agrovision-c0b3e.firebaseapp.com',
	projectId: 'agrovision-c0b3e',
	storageBucket: 'agrovision-c0b3e.appspot.com',
	messagingSenderId: 'REPLACE_WITH_FIREBASE_MESSAGING_SENDER_ID',
	appId: 'REPLACE_WITH_FIREBASE_APP_ID',
};

const lastSearchPrefix = 'agrovision:last-search:';
const authMessage = document.getElementById('auth-message');
const authPanel = document.getElementById('auth-panel');
const headerSigninButton = document.getElementById('header-signin-button');
const headerSignoutButton = document.getElementById('header-signout-button');
const headerUserChip = document.getElementById('header-user-chip');
const navAuthState = document.getElementById('nav-auth-state');
const googleSigninButton = document.getElementById('google-signin-button');
const emailSigninForm = document.getElementById('email-signin-form');
const createAccountButton = document.getElementById('create-account-button');
const openAppButton = document.getElementById('open-app-button');
const openAppLinkButton = document.getElementById('open-app-link-button');
const authEmailInput = document.getElementById('auth-email');
const authPasswordInput = document.getElementById('auth-password');
const historyHover = document.getElementById('history-hover');
const historyHoverEmpty = document.getElementById('history-hover-empty');
const historyHoverList = document.getElementById('history-hover-list');
const lastSearchCard = document.getElementById('last-search-card');
const lastSearchMeta = document.getElementById('last-search-meta');
const lastSearchName = document.getElementById('last-search-name');
const lastSearchTimestamp = document.getElementById('last-search-timestamp');
const lastSearchLink = document.getElementById('last-search-link');
const isAuthPage = window.location.pathname.endsWith('/auth.html') || window.location.pathname.endsWith('auth.html');
const appPageUrl = new URL('index.html', window.location.href).toString();
const authPageUrl = new URL('auth.html', window.location.href).toString();

let currentUser = null;
let authReady = false;
let authReadyResolver;

const authReadyPromise = new Promise((resolve) => {
	authReadyResolver = resolve;
});

function hasFirebaseConfig() {
	return Object.values(firebaseConfig).every(
		(value) => typeof value === 'string' && !value.startsWith('REPLACE_WITH_'),
	);
}

function getLastSearchKey(uid) {
	return `${lastSearchPrefix}${uid}`;
}

function getHistoryKey(uid) {
	return `${lastSearchPrefix}${uid}:history`;
}

function formatTimestamp(value) {
	if (!value) {
		return '';
	}

	const date = new Date(value);
	if (Number.isNaN(date.getTime())) {
		return '';
	}

	return date.toLocaleString([], {
		dateStyle: 'medium',
		timeStyle: 'short',
	});
}

function setAuthMessage(message, isError = false) {
	if (!authMessage) {
		return;
	}

	authMessage.textContent = message;
	authMessage.style.backgroundColor = isError ? 'rgba(220, 38, 38, 0.12)' : '';
	authMessage.style.color = isError ? 'rgb(153, 27, 27)' : '';
}

function setLastSearchEmpty(message) {
	if (lastSearchMeta) {
		lastSearchMeta.textContent = message;
	}
	if (lastSearchCard) {
		lastSearchCard.hidden = true;
	}
}

function getSearchHistory(uid) {
	if (!uid) {
		return [];
	}

	const storedValue = localStorage.getItem(getHistoryKey(uid));
	if (!storedValue) {
		const singleRecord = getLastSearch(uid);
		return singleRecord ? [singleRecord] : [];
	}

	try {
		const parsedHistory = JSON.parse(storedValue);
		return Array.isArray(parsedHistory) ? parsedHistory : [];
	} catch (error) {
		return [];
	}
}

function renderHistoryList(history) {
	if (!historyHoverList || !historyHoverEmpty) {
		return;
	}

	if (!history.length) {
		historyHoverEmpty.hidden = false;
		historyHoverList.hidden = true;
		historyHoverList.innerHTML = '';
		return;
	}

	historyHoverEmpty.hidden = true;
	historyHoverList.hidden = false;
	historyHoverList.innerHTML = history
		.map((record) => {
			const timestamp = formatTimestamp(record.timestamp);
			return `
				<article class="history-hover__item">
					<div class="history-hover__item-name">${record.displayName || record.disease || 'Unknown disease'}</div>
					<div class="history-hover__item-meta">${timestamp || 'No timestamp available'}</div>
					${record.detailsUrl ? `<a class="history-hover__item-link" href="${record.detailsUrl}" target="_blank" rel="noreferrer">Open details</a>` : ''}
				</article>
			`;
		})
		.join('');
}

function renderLastSearch(record) {
	if (!record) {
		setLastSearchEmpty('No saved disease yet.');
		return;
	}

	if (lastSearchMeta) {
		lastSearchMeta.textContent = 'Most recent prediction saved on this device.';
	}
	if (lastSearchCard) {
		lastSearchCard.hidden = false;
	}
	if (lastSearchName) {
		lastSearchName.textContent = record.displayName || record.disease || 'Unknown disease';
	}
	if (lastSearchTimestamp) {
		lastSearchTimestamp.textContent = formatTimestamp(record.timestamp);
	}
	if (lastSearchLink) {
		lastSearchLink.href = record.detailsUrl || '#';
		lastSearchLink.hidden = !record.detailsUrl;
	}
}

function getLastSearch(uid) {
	if (!uid) {
		return null;
	}

	const storedValue = localStorage.getItem(getLastSearchKey(uid));
	if (!storedValue) {
		return null;
	}

	try {
		return JSON.parse(storedValue);
	} catch (error) {
		return null;
	}
}

function saveLastSearch(record) {
	if (!currentUser) {
		return null;
	}

	const normalizedRecord = {
		disease: record.disease,
		displayName: record.displayName || record.disease,
		detailsUrl: record.detailsUrl || '',
		percentage: record.percentage ?? null,
		predictionTime: record.predictionTime ?? null,
		timestamp: record.timestamp || new Date().toISOString(),
	};

	const existingHistory = getSearchHistory(currentUser.uid);
	const updatedHistory = [normalizedRecord, ...existingHistory].slice(0, 10);
	localStorage.setItem(getLastSearchKey(currentUser.uid), JSON.stringify(normalizedRecord));
	localStorage.setItem(getHistoryKey(currentUser.uid), JSON.stringify(updatedHistory));
	renderLastSearch(normalizedRecord);
	renderHistoryList(updatedHistory);
	return normalizedRecord;
}

function updateHeaderState() {
	const signedIn = Boolean(currentUser);

	if (signedIn && isAuthPage) {
		window.location.replace(appPageUrl);
		return;
	}

	if (headerSigninButton) {
		headerSigninButton.hidden = signedIn;
	}
	if (headerSignoutButton) {
		headerSignoutButton.hidden = !signedIn;
	}
	if (headerUserChip) {
		headerUserChip.hidden = !signedIn;
		headerUserChip.textContent = signedIn ? (currentUser.displayName || currentUser.email || 'Signed in') : '';
	}
	if (navAuthState) {
		navAuthState.classList.toggle('is-signed-in', signedIn);
	}
	if (historyHover) {
		historyHover.hidden = !signedIn;
	}
	if (authPanel) {
		authPanel.hidden = signedIn;
	}
	if (signedIn) {
		setAuthMessage(`Signed in as ${currentUser.displayName || currentUser.email || 'your account'}.`);
		const history = getSearchHistory(currentUser.uid);
		renderLastSearch(history[0] || null);
		renderHistoryList(history);
	} else {
		setAuthMessage(hasFirebaseConfig() ? 'Sign in to continue.' : 'Add your Firebase config in Frontend/js/auth.js before sign-in can work.', !hasFirebaseConfig());
		setLastSearchEmpty('Sign in to view your saved disease search.');
		renderHistoryList([]);
	}
}

function scrollToAuthPanel() {
	if (authPanel && !authPanel.hidden) {
		authPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
}

function openAppPage() {
	window.location.href = appPageUrl;
}

function openAuthPage() {
	window.location.href = authPageUrl;
}

async function signInWithGoogle() {
	if (!window.firebase || !hasFirebaseConfig()) {
		setAuthMessage('Firebase config is missing. Replace the placeholders in Frontend/js/auth.js.', true);
		return;
	}

	try {
		const provider = new firebase.auth.GoogleAuthProvider();
		await firebase.auth().signInWithPopup(provider);
	} catch (error) {
		setAuthMessage(error.message || 'Google sign-in failed.', true);
	}
}

async function signInWithEmailPassword(isCreateAccount = false) {
	if (!window.firebase || !hasFirebaseConfig()) {
		setAuthMessage('Firebase config is missing. Replace the placeholders in Frontend/js/auth.js.', true);
		return;
	}

	const email = authEmailInput.value.trim();
	const password = authPasswordInput.value.trim();

	if (!email || !password) {
		setAuthMessage('Enter both email and password.', true);
		return;
	}

	try {
		if (isCreateAccount) {
			await firebase.auth().createUserWithEmailAndPassword(email, password);
		} else {
			await firebase.auth().signInWithEmailAndPassword(email, password);
		}
	} catch (error) {
		setAuthMessage(error.message || 'Email sign-in failed.', true);
	}
}

async function signOut() {
	if (!window.firebase || !hasFirebaseConfig()) {
		return;
	}

	await firebase.auth().signOut();
	if (!isAuthPage) {
		window.location.replace(authPageUrl);
	}
}

function initAuth() {
	if (!hasFirebaseConfig()) {
		authReady = true;
		authReadyResolver();
		if (isAuthPage) {
			setAuthMessage('Add your Firebase web config in Frontend/js/auth.js to enable sign-in.', true);
		}
		return;
	}

	firebase.initializeApp(firebaseConfig);
	firebase.auth().onAuthStateChanged((user) => {
		currentUser = user;
		authReady = true;
		updateHeaderState();
		authReadyResolver();
	});
}

document.addEventListener('DOMContentLoaded', () => {
	if (headerSigninButton) {
		headerSigninButton.addEventListener('click', openAuthPage);
	}
	if (headerSignoutButton) {
		headerSignoutButton.addEventListener('click', () => {
			signOut().catch((error) => setAuthMessage(error.message || 'Sign out failed.', true));
		});
	}
	if (openAppButton) {
		openAppButton.addEventListener('click', openAppPage);
	}
	if (openAppLinkButton) {
		openAppLinkButton.addEventListener('click', openAppPage);
	}
	if (googleSigninButton) {
		googleSigninButton.addEventListener('click', () => {
			signInWithGoogle();
		});
	}
	if (emailSigninForm) {
		emailSigninForm.addEventListener('submit', (event) => {
			event.preventDefault();
			signInWithEmailPassword(false);
		});
	}
	if (createAccountButton) {
		createAccountButton.addEventListener('click', () => {
			signInWithEmailPassword(true);
		});
	}

	initAuth();
});

window.AgroVisionAuth = {
	ready: () => authReadyPromise,
	getCurrentUser: () => currentUser,
	getLastSearch,
	saveLastSearch,
	renderLastSearch,
	setAuthMessage,
	scrollToAuthPanel,
	getLastSearchKey,
};