/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#337ab7',
          dark: '#286090',
          light: '#eaf3fb',
        },
        page: '#f1f5fd',
        sidebar: '#f4f5f9',
        table: {
          purple: '#6a00c9',
          lavender: '#e1cdf2',
        },
        severity: {
          1: '#22c55e',   // green
          2: '#84cc16',   // lime
          3: '#f59e0b',   // amber
          4: '#f97316',   // orange
          5: '#ef4444',   // red
        },
      },
    },
  },
  plugins: [],
}
