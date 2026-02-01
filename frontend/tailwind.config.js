/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: '#FF5F1F', // Orange from the logo text in user code
            },
            fontFamily: {
                outfit: ['sans-serif'], // Fallback since we don't have font files yet
            }
        },
    },
    plugins: [],
}
