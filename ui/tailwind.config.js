/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{ts,tsx}', './index.html'],
  theme: {
    extend: {
      colors: {
        // Design tokens — referenced via CSS variables from index.css.
        // Kept in `extend` so we can compose with Tailwind's defaults.
        brand: {
          50: '#EFF6FF',
          500: '#2563EB',
          600: '#1D4ED8',
          700: '#1E40AF',
        },
      },
    },
  },
  plugins: [],
};
