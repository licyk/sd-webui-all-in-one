(function () {
    const siteScriptConfig = {
        src: "https://licyk-umami.netlify.app/script.js",
        "data-website-id": "308fc79d-d064-456b-9e02-5d45b944e030",
    };

    function loadSiteScript() {
        const selector = `script[src="${siteScriptConfig.src}"][data-website-id="${siteScriptConfig["data-website-id"]}"]`;
        if (document.querySelector(selector)) {
            return;
        }

        const script = document.createElement("script");
        for (const [key, value] of Object.entries(siteScriptConfig)) {
            script.setAttribute(key, value);
        }
        script.async = true;

        document.head.appendChild(script);
    }

    // Inject after the window load event so a slow or unreachable analytics
    // host can never delay page load.
    function scheduleSiteScript() {
        if ("requestIdleCallback" in window) {
            window.requestIdleCallback(loadSiteScript, { timeout: 3000 });
        } else {
            window.setTimeout(loadSiteScript, 0);
        }
    }

    if (document.readyState === "complete") {
        scheduleSiteScript();
    } else {
        window.addEventListener("load", scheduleSiteScript, { once: true });
    }
})();
