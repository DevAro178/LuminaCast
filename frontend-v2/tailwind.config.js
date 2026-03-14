/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#2C4A4A',
        card: '#1A3333',
        surface: '#FFFFFF',
        accent: '#4A7A7A',
        textPrimary: '#FFFFFF',
        textSecondary: '#B0C4C4',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
      },
      borderRadius: {
        'xl': '20px',
        '2xl': '24px',
      }
    },
  },
  plugins: [require("tailwindcss-animate")],
}
