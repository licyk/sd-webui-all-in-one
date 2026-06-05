(function () {
    const umamiConfig = {
        src: "https://licyk-blog-umami.netlify.app/script.js",
        "data-website-id": "308fc79d-d064-456b-9e02-5d45b944e030",
        defer: "",
    };

    function loadUmami() {
        const selector = `script[src="${umamiConfig.src}"][data-website-id="${umamiConfig["data-website-id"]}"]`;
        if (document.querySelector(selector)) {
            return;
        }

        const script = document.createElement("script");
        for (const [key, value] of Object.entries(umamiConfig)) {
            script.setAttribute(key, value);
        }

        document.head.appendChild(script);
    }

    if (typeof document$ !== "undefined") {
        document$.subscribe(loadUmami);
    } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadUmami);
    } else {
        loadUmami();
    }
})();
