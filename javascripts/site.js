(function () {
    const siteScriptConfig = {
        src: "https://licyk-umami.netlify.app/script.js",
        "data-website-id": "308fc79d-d064-456b-9e02-5d45b944e030",
        defer: "",
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

        document.head.appendChild(script);
    }

    if (typeof document$ !== "undefined") {
        document$.subscribe(loadSiteScript);
    } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadSiteScript);
    } else {
        loadSiteScript();
    }
})();
