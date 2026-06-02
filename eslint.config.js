import js from "@eslint/js";
import noUnsanitized from "eslint-plugin-no-unsanitized";

export default [
    js.configs.recommended,
    {
        files: ["static/js/**/*.js"],
        plugins: {
            "no-unsanitized": noUnsanitized,
        },
        rules: {
            "no-unsanitized/method": "error",
            "no-unsanitized/property": "error",
            "no-unused-vars": "warn",
            "no-undef": "off", // since we have window. / browser globals
        },
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                window: "readonly",
                document: "readonly",
                console: "readonly",
                setTimeout: "readonly",
                setInterval: "readonly",
                clearTimeout: "readonly",
                clearInterval: "readonly",
                fetch: "readonly",
                FormData: "readonly",
                URLSearchParams: "readonly",
                DOMParser: "readonly",
                Event: "readonly",
                CustomEvent: "readonly",
            }
        }
    }
];
