/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Polymarket-inspired dark theme
        gray: {
          900: '#0d1117',
          800: '#161b22',
          700: '#21262d',
          600: '#30363d',
          500: '#484f58',
          400: '#6e7681',
          300: '#8b949e',
          200: '#c9d1d9',
          100: '#f0f6fc',
        },
        // Custom colors for probabilities
        probability: {
          yes: '#10b981',   // Green for YES
          no: '#ef4444',    // Red for NO
          neutral: '#6b7280',
        },
        // Status colors
        status: {
          active: '#10b981',
          resolved: '#6b7280',
          warning: '#f59e0b',
        }
      },
    },
  },
  plugins: [],
}
