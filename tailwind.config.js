/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
    './apps/**/forms.py'
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#FFC880',
        'primary-container': '#FFC880',
      },
      fontFamily: {
        'sans': ['Manrope', 'sans-serif'],
        'newsreader': ['Newsreader', 'serif'],
        'grotesk': ['Space Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
