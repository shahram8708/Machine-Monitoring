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

document.addEventListener("DOMContentLoaded", () => {
	const toggle = document.getElementById("sidebarToggle");
	const backdrop = document.getElementById("sidebar-backdrop");
	const links = document.querySelectorAll("#sidebar .nav-link");

	const closeSidebar = () => document.body.classList.remove("sidebar-open");

	if (toggle) {
		toggle.addEventListener("click", () => {
			document.body.classList.toggle("sidebar-open");
		});
	}

	if (backdrop) {
		backdrop.addEventListener("click", closeSidebar);
	}

	links.forEach((link) => link.addEventListener("click", closeSidebar));

	window.addEventListener("resize", () => {
		if (window.innerWidth >= 992) {
			closeSidebar();
		}
	});
});
