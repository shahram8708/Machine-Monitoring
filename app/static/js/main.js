(function () {
	const badge = document.getElementById("alert-count-badge");
	const dropdown = document.querySelector(".dropdown-menu[data-alerts]");

	const render = (payload) => {
		if (!badge) return;
		const count = payload.count || 0;
		badge.textContent = count > 99 ? "99+" : String(count || "");
		badge.style.display = count ? "inline-block" : "none";
	};

	const poll = () => {
		fetch("/alerts/unread", { cache: "no-store" })
			.then((res) => res.json())
			.then((data) => render(data))
			.catch(() => {});
	};

	if (badge) {
		poll();
		setInterval(poll, 15000);
	}
})();
