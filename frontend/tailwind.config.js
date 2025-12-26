/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        // Brand colors for inventory page
        brand: {
          orange: '#EB5C20',
          'orange-light': '#F5A173',
          'orange-dark': '#C74A18',
          gray: '#9FA0A0',
          'gray-light': '#C5C6C6',
          'gray-dark': '#6B6C6C',
        },
      },
    },
  },
  plugins: [],
}
